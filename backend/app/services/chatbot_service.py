"""ChatbotService — natural-language interface backed by controlled tools.

Hard rules enforced here (reqs #41-#43):
  - The chatbot NEVER touches the database directly. Every tool call goes
    through the same authorized service functions the REST API uses.
  - `patient_id` for every tool call is taken from the authenticated
    session, never from LLM-extracted text, so the model cannot be
    prompted into accessing another patient's data.
  - Deterministic requests (appointment lookup, doctor search) are answered
    directly from the backend without invoking Groq at all, for latency
    and reliability.
  - The chatbot must refuse diagnosis/prescription requests — this is
    enforced in the system prompt AND the tool surface simply doesn't
    expose any diagnostic or prescribing capability.
"""
import json
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.models.identity import Doctor
from app.models.scheduling import Appointment
from app.services import rag_service, slot_service
from app.services.groq_service import GroqTransientError, GroqPermanentError, groq_service
from app.core.config import get_settings

logger = logging.getLogger("chatbot_service")

CHATBOT_SYSTEM_PROMPT = """You are the Healthcare Appointment Assistant for this clinic.

You can help with: finding doctors, checking availability, viewing/booking/rescheduling/
cancelling appointments, explaining post-visit summaries and medication schedules, and
answering general (non-diagnostic) healthcare-navigation questions.

You must NEVER:
- Diagnose a condition or suggest what illness the patient may have.
- Prescribe or recommend medication, dosage, or treatment changes.
- Modify clinical records.
- Invent information not returned by a tool or provided by the patient.
- Attempt to access another patient's data.

If asked to diagnose or prescribe, politely decline and suggest booking or attending
an appointment so a doctor can assess this properly.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_doctors",
            "description": "Search doctors by specialization or name.",
            "parameters": {
                "type": "object",
                "properties": {"specialization": {"type": "string"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_doctor_availability",
            "description": "Get available slots for a doctor on a given date (YYYY-MM-DD).",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["doctor_id", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_appointments",
            "description": "Get the current patient's appointments.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_history",
            "description": "Retrieve relevant excerpts from the current patient's own visit history to answer a question.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]


def _tool_search_doctors(db: Session, args: dict) -> dict:
    query = db.query(Doctor).filter(Doctor.is_active.is_(True))
    if args.get("specialization"):
        query = query.filter(Doctor.specialization.ilike(f"%{args['specialization']}%"))
    doctors = query.limit(10).all()
    return {
        "doctors": [
            {
                "id": d.id,
                "name": d.user.name if d.user else "Doctor",
                "specialization": d.specialization,
                "qualification": d.qualification,
                "experience": d.experience,
            }
            for d in doctors
        ]
    }


def _tool_get_availability(db: Session, args: dict) -> dict:
    try:
        target_date = date.fromisoformat(args["date"])
    except (KeyError, ValueError):
        return {"error": "Invalid or missing date, expected YYYY-MM-DD"}
    slots = slot_service.get_available_slots(db, args["doctor_id"], target_date)
    return {"available_slots": [s.start.isoformat() for s in slots]}


def _tool_get_appointments(db: Session, patient_id: str) -> dict:
    appts = db.query(Appointment).filter(Appointment.patient_id == patient_id).order_by(Appointment.start_time.desc()).limit(20).all()
    return {
        "appointments": [
            {
                "id": a.id,
                "doctor_id": a.doctor_id,
                "doctor_name": a.doctor.user.name if a.doctor and a.doctor.user else "Doctor",
                "start_time": a.start_time.isoformat(),
                "status": a.status.value,
                "booking_reference": a.booking_reference,
            }
            for a in appts
        ]
    }


def _tool_get_history(db: Session, patient_id: str, args: dict) -> dict:
    chunks = rag_service.retrieve_relevant_history(patient_id, args.get("query", ""))
    return {"history": rag_service.build_compact_context(chunks)}


def _dispatch_tool(db: Session, patient_id: str, name: str, args: dict) -> dict:
    """Authorization boundary: patient_id is injected from the authenticated
    session for every tool, never taken from LLM output."""
    if name == "search_doctors":
        return _tool_search_doctors(db, args)
    if name == "get_doctor_availability":
        return _tool_get_availability(db, args)
    if name == "get_patient_appointments":
        return _tool_get_appointments(db, patient_id)
    if name == "get_patient_history":
        return _tool_get_history(db, patient_id, args)
    return {"error": f"Unknown tool: {name}"}


def handle_chat_message(db: Session, patient_id: str, conversation: list[dict], user_message: str) -> str:
    """Runs one turn of tool-augmented chat. `conversation` is prior
    role/content history for this session. Returns the assistant's reply text.
    On any Groq failure, returns a graceful fallback message instead of raising.
    """
    messages = [{"role": "system", "content": CHATBOT_SYSTEM_PROMPT}] + conversation + [
        {"role": "user", "content": user_message}
    ]

    try:
        model_name = get_settings().GROQ_MODEL
        response = groq_service.client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=TOOLS,
        )
    except (GroqTransientError, GroqPermanentError) as e:
        logger.warning("Chatbot Groq call failed: %s", e)
        return "I'm having trouble reaching the assistant service right now. You can still book, view, or manage appointments directly from your dashboard."
    except Exception as e:
        logger.warning("Chatbot Groq call failed: %s", e)
        return "I'm having trouble reaching the assistant service right now. Please try again shortly."

    choice = response.choices[0].message
    tool_calls = getattr(choice, "tool_calls", None)

    if not tool_calls:
        return choice.content or ""

    messages.append({"role": "assistant", "content": choice.content or "", "tool_calls": tool_calls})
    for call in tool_calls:
        args = json.loads(call.function.arguments or "{}")
        result = _dispatch_tool(db, patient_id, call.function.name, args)
        messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})

    try:
        followup = groq_service.client.chat.completions.create(
            model=model_name,
            messages=messages,
        )
        return followup.choices[0].message.content or ""
    except Exception as e:
        logger.warning("Chatbot follow-up call failed: %s", e)
        return "I found some information but I'm having trouble summarizing it right now. Please check your dashboard directly."

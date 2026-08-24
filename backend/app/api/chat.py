from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_patient
from app.models.identity import Patient
from app.models.messaging import ChatMessage, ChatSession
from app.schemas.api import ChatMessageRequest, ChatMessageResponse
from app.services import chatbot_service, rag_service

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/sessions", status_code=201)
def create_session(patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    session = ChatSession(patient_id=patient.id)
    db.add(session)
    db.commit()
    return {"id": session.id, "status": session.status}


@router.get("/chat/sessions")
def list_sessions(patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).filter(ChatSession.patient_id == patient.id).order_by(ChatSession.created_at.desc()).all()
    return [{"id": s.id, "status": s.status, "created_at": s.created_at.isoformat()} for s in sessions]


@router.post("/chat/sessions/{session_id}/messages", response_model=ChatMessageResponse)
def send_message(session_id: str, payload: ChatMessageRequest, patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    session = db.get(ChatSession, session_id)
    if not session or session.patient_id != patient.id:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "Chat session not found."})

    prior = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    conversation = [{"role": m.role, "content": m.message} for m in prior]

    db.add(ChatMessage(session_id=session_id, role="user", message=payload.message))
    db.flush()

    reply = chatbot_service.handle_chat_message(db, patient.id, conversation, payload.message)

    db.add(ChatMessage(session_id=session_id, role="assistant", message=reply))
    db.commit()

    return ChatMessageResponse(session_id=session_id, reply=reply)


@router.get("/patients/me/history")
def get_own_history(patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    from app.models.messaging import PatientHistoryDocument

    docs = db.query(PatientHistoryDocument).filter(PatientHistoryDocument.patient_id == patient.id).order_by(PatientHistoryDocument.created_at.desc()).all()
    return [{"id": d.id, "type": d.document_type, "created_at": d.created_at.isoformat()} for d in docs]


@router.get("/patients/me/history/relevant")
def get_relevant_history(query: str, patient: Patient = Depends(get_current_patient)):
    chunks = rag_service.retrieve_relevant_history(patient.id, query)
    return {"context": rag_service.build_compact_context(chunks)}

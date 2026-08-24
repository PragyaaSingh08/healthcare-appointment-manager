# LLM Prompts Documentation

This document details all prompts used in the AI-powered features of the Healthcare Appointment System.

---

## Pre-Visit Symptom Analysis Prompt

### Prompt Name

`pre_visit_symptom_analysis`

### Purpose

Analyze patient-reported symptoms before the appointment to generate a structured summary for the doctor, including urgency assessment and suggested questions.

### Input

- `symptoms` (string): Patient's self-reported symptoms
- `patient_age` (integer, optional): Patient's age
- `patient_gender` (string, optional): Patient's gender
- `medical_history` (string, optional): Relevant medical history

### Output

```json
{
  "urgency": "Low | Medium | High",
  "chief_complaint": "string",
  "suggested_questions": ["string", "string", "string"],
  "confidence_score": 0.0-1.0
}
```

### Prompt Template

```text
You are an experienced medical assistant analyzing patient symptoms before a doctor's appointment.

PATIENT INFORMATION:
Age: {patient_age}
Gender: {patient_gender}
Medical History: {medical_history}

SYMPTOMS REPORTED:
{symptoms}

TASK:
Analyze the symptoms and provide the following information in JSON format:

URGENCY LEVEL: Classify as "Low", "Medium", or "High"
- Low: Non-urgent, routine consultation
- Medium: Should be seen within 24-48 hours
- High: Urgent, requires immediate attention

CHIEF COMPLAINT: Summarize the primary concern in one clear sentence

SUGGESTED QUESTIONS: Provide exactly 3 specific questions the doctor should ask to better understand the condition. Questions should be:
- Relevant to the symptoms
- Help narrow down differential diagnosis
- Identify red flags or concerning features

CONFIDENCE SCORE: Rate your confidence (0.0 to 1.0) based on clarity of symptoms

OUTPUT FORMAT (JSON ONLY, NO OTHER TEXT):
{
  "urgency": "Low|Medium|High",
  "chief_complaint": "...",
  "suggested_questions": ["...", "...", "..."],
  "confidence_score": 0.0
}

IMPORTANT:
- Do not provide medical advice or diagnosis
- Do not explain your reasoning
- Output ONLY valid JSON
- If symptoms are unclear, set confidence_score lower
```

### Design Rationale

1. **Structured Output**: JSON format ensures consistent parsing and database storage
2. **Urgency Classification**: Helps doctors prioritize appointments
3. **Suggested Questions**: Reduces doctor's cognitive load, ensures thorough history-taking
4. **Confidence Score**: Allows system to flag low-confidence summaries for doctor review
5. **No Medical Advice**: Explicit instruction prevents LLM from overstepping

### Expected Output Format

```json
{
  "urgency": "Medium",
  "chief_complaint": "Fever with body pain and fatigue for 3 days",
  "suggested_questions": [
    "What was the highest temperature recorded?",
    "Have you taken any medication for fever? If yes, what was the response?",
    "Any recent travel or contact with sick individuals?"
  ],
  "confidence_score": 0.85
}
```

### Failure Handling

1. **Timeout**: If LLM takes >30 seconds, return fallback response
2. **Invalid JSON**: Retry once, then use manual entry
3. **Missing Fields**: Fill missing fields with defaults:
   - `urgency`: "Medium"
   - `chief_complaint`: symptoms truncated to 100 chars
   - `suggested_questions`: ["Please describe symptoms in detail", "When did symptoms start?", "Any medication taken?"]
   - `confidence_score`: 0.5

### Fallback Prompt

```text
If AI analysis fails, display:
"Pre-visit summary generation unavailable. Doctor will review symptoms during consultation."

Store in database:
{
  "urgency": "Medium",
  "chief_complaint": "{symptoms[:100]}...",
  "suggested_questions": [
    "Please describe symptoms in detail",
    "When did symptoms start?",
    "Any medication taken?"
  ],
  "confidence_score": 0.5,
  "is_fallback": true
}
```

---

## Post-Visit Summary Prompt

### Prompt Name

`post_visit_summary_generation`

### Purpose

Convert doctor's clinical notes into a patient-friendly summary with clear medication instructions and follow-up steps.

### Input

- `clinical_notes` (string): Doctor's clinical notes
- `diagnosis` (string): Doctor's diagnosis
- `prescription` (array): List of medications with dosage and frequency
- `follow_up_instructions` (string): Doctor's follow-up guidance

### Output

```json
{
  "summary": "string",
  "medication_schedule": ["string", "..."],
  "follow_up_steps": ["string", "..."],
  "warnings": ["string", "..."],
  "confidence_score": 0.0-1.0
}
```

### Prompt Template

```text
You are a medical communication specialist translating clinical notes into patient-friendly language.

CLINICAL NOTES:
{clinical_notes}

DIAGNOSIS:
{diagnosis}

PRESCRIPTION:
{prescription}

FOLLOW-UP INSTRUCTIONS:
{follow_up_instructions}

TASK:
Create a patient-friendly summary with the following sections:

SUMMARY: Explain the diagnosis and condition in simple, reassuring language (2-3 sentences). Avoid medical jargon.

MEDICATION SCHEDULE: For each medication, provide clear instructions:
- Medication name
- Dosage
- When to take (morning, afternoon, night, with food, etc.)
- Duration

FOLLOW-UP STEPS: List actionable steps the patient should take (3-5 items):
- Lifestyle modifications
- Warning signs to watch for
- When to follow up
- Self-care instructions

WARNINGS: List any red flags that require immediate medical attention (2-3 items)

CONFIDENCE SCORE: Rate your confidence (0.0 to 1.0)

OUTPUT FORMAT (JSON ONLY, NO OTHER TEXT):
{
  "summary": "...",
  "medication_schedule": ["...", "..."],
  "follow_up_steps": ["...", "...", "..."],
  "warnings": ["...", "..."],
  "confidence_score": 0.0
}

IMPORTANT:
- Use simple, clear language (8th grade reading level)
- Be empathetic and reassuring
- Do not provide additional medical advice beyond what the doctor noted
- Output ONLY valid JSON
```

### Design Rationale

1. **Patient-Friendly Language**: Ensures comprehension across education levels
2. **Structured Medication Schedule**: Improves adherence
3. **Actionable Follow-Up Steps**: Clear guidance reduces confusion
4. **Warnings Section**: Safety-critical information highlighted
5. **Empathetic Tone**: Reduces patient anxiety

### Expected Output Format

```json
{
  "summary": "You have been diagnosed with viral fever, which is a common infection caused by a virus. This typically resolves on its own within 5-7 days with proper rest and hydration.",
  "medication_schedule": [
    "Paracetamol 500mg - Take 1 tablet twice daily (morning and night) for 5 days. Take with food if you experience stomach discomfort.",
    "Vitamin C 500mg - Take 1 tablet once daily in the morning for 7 days to support your immune system."
  ],
  "follow_up_steps": [
    "Rest and get plenty of sleep to help your body recover",
    "Drink at least 8-10 glasses of water daily to stay hydrated",
    "Monitor your temperature twice daily and record it",
    "Follow up with your doctor if fever persists beyond 5 days or worsens",
    "Avoid contact with others to prevent spreading the infection"
  ],
  "warnings": [
    "Seek immediate medical attention if you develop difficulty breathing or chest pain",
    "Contact your doctor if fever exceeds 103°F (39.4°C) or if you develop a rash"
  ],
  "confidence_score": 0.92
}
```

### Failure Handling

1. **Timeout**: If LLM takes >30 seconds, use fallback
2. **Invalid JSON**: Retry once, then use template
3. **Missing Fields**: Fill with defaults

### Fallback Template

```text
If AI generation fails, display:
"Your doctor's notes are being processed. Please refer to the prescription provided."

Store in database:
{
  "summary": "Please refer to your doctor's notes and prescription below.",
  "medication_schedule": ["See prescription details"],
  "follow_up_steps": ["Follow your doctor's instructions", "Contact clinic if you have questions"],
  "warnings": ["Seek immediate care if symptoms worsen"],
  "confidence_score": 0.5,
  "is_fallback": true
}
```

---

## Medication Reminder Prompt

### Prompt Name

`medication_reminder_message`

### Purpose

Generate personalized medication reminder messages for patients.

### Input

- `patient_name` (string)
- `medications` (array): List of medications with timing
- `time_of_day` (string): Morning/Afternoon/Night

### Output

```json
{
  "title": "string",
  "message": "string",
  "medications_list": ["string", "..."]
}
```

### Prompt Template

```text
Generate a friendly medication reminder message.

PATIENT: {patient_name}
TIME: {time_of_day}
MEDICATIONS: {medications}

Create a warm, encouraging reminder message.

OUTPUT FORMAT (JSON ONLY):
{
  "title": "Time for your medications!",
  "message": "Hi {patient_name}, it's time to take your {time_of_day} medications. Taking your medications as prescribed helps you stay healthy!",
  "medications_list": ["Medication 1: dosage", "Medication 2: dosage"]
}
```

---

## Doctor Leave Notification Prompt

### Prompt Name

`doctor_leave_reschedule_notification`

### Purpose

Generate empathetic notification messages when appointments are affected by doctor leave.

### Input

- `patient_name` (string)
- `doctor_name` (string)
- `original_date` (string)
- `reason` (string)

### Output

```json
{
  "title": "string",
  "message": "string",
  "action_required": "string"
}
```

### Prompt Template

```text
Generate a notification for appointment rescheduling due to doctor leave.

PATIENT: {patient_name}
DOCTOR: {doctor_name}
ORIGINAL APPOINTMENT: {original_date}
REASON: {reason}

Create an empathetic, professional message.

OUTPUT FORMAT (JSON ONLY):
{
  "title": "Appointment Rescheduling Required",
  "message": "Dear {patient_name}, Dr. {doctor_name} will be unavailable on {original_date} due to {reason}. We apologize for any inconvenience. Please reschedule your appointment at your earliest convenience.",
  "action_required": "Please log in to reschedule your appointment"
}
```

---

## RAG Prompts (Not Implemented)

### Status

Partially Implemented - Framework in place, not actively used.

### Planned Implementation

Future enhancement to include:
- Medical knowledge base retrieval
- Drug interaction checking
- Symptom-disease matching

---

## Prompt Testing Strategy

### Test Cases

1. **Clear Symptoms**: Well-defined symptoms should yield high confidence
2. **Vague Symptoms**: Unclear symptoms should yield lower confidence
3. **Emergency Symptoms**: Chest pain, difficulty breathing should trigger "High" urgency
4. **Chronic Conditions**: Should consider medical history
5. **Pediatric Patients**: Age-appropriate considerations

### Validation

- JSON schema validation before database storage
- Confidence score threshold alerts (<0.6 flagged for review)
- Manual review queue for low-confidence summaries

---

## LLM Provider Configuration

### Supported Providers

1. **Groq** (Primary)
   - Model: `llama-3.1-70b-versatile` / `openai/gpt-oss-20b`
   - Timeout: 30 seconds
   - Cost: Low

2. **OpenAI** (Fallback)
   - Model: `gpt-4o-mini`
   - Timeout: 30 seconds
   - Cost: Medium

3. **Anthropic** (Fallback)
   - Model: `claude-3-haiku-20240307`
   - Timeout: 30 seconds
   - Cost: Low

### Provider Selection Logic

```python
def get_llm_provider():
    if config.LLM_PROVIDER == "groq" and groq_available():
        return GroqClient()
    elif config.LLM_PROVIDER == "openai" and openai_available():
        return OpenAIClient()
    elif config.LLM_PROVIDER == "anthropic" and anthropic_available():
        return AnthropicClient()
    else:
        return FallbackClient()  # Manual entry
```

### Rate Limiting

- Groq: 30 requests/minute
- OpenAI: 60 requests/minute
- Implement exponential backoff on 429 errors

---

## Security Considerations

1. **No PHI in Prompts**: Avoid sending identifiable information
2. **Data Minimization**: Only send necessary symptom data
3. **Encryption**: LLM API calls over HTTPS
4. **Audit Logs**: Log all LLM requests for compliance
5. **Data Retention**: Summaries stored per retention policy

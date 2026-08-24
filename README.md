# Healthcare Appointment & Follow-up Manager

A clinic platform with separate patient, doctor, and admin portals: booking with concurrency-safe slot holds, AI pre-/post-visit summaries (Groq), patient-history RAG (ChromaDB), an AI assistant chatbot, email notifications, and Google Calendar sync for both patient and doctor.

# 🌐 Live Deployment

| Service | URL |
|----------|------|
| Frontend (Vercel) | https://healthcare-appointment-ma-git-3fcb5f-pragyas1008-1004s-projects.vercel.app |
| Backend API (Railway) | https://healthcare-appointment-manager-production-831c.up.railway.app |
| Swagger API Docs | https://healthcare-appointment-manager-production-831c.up.railway.app/docs |
| ReDoc API Docs | https://healthcare-appointment-manager-production-831c.up.railway.app/redoc |

### Quick Access

- 🚀 Frontend Demo: https://healthcare-appointment-ma-git-3fcb5f-pragyas1008-1004s-projects.vercel.app
- 🔧 Backend API: https://healthcare-appointment-manager-production-831c.up.railway.app
- 📚 Swagger Docs: https://healthcare-appointment-manager-production-831c.up.railway.app/docs
- 📖 ReDoc Docs: https://healthcare-appointment-manager-production-831c.up.railway.app/redoc

See SYSTEM_DESIGN.md for the architecture write-up (double-booking prevention, leave conflicts, notification/calendar failure handling, latency).

Status of this build
This codebase was built and verified in a sandboxed dev environment:

34/34 backend tests pass, including a real concurrency test (12 simultaneous threads booking the same doctor+slot against a live Postgres instance → exactly 1 success, 11 conflicts, 1 DB row), regression tests for three bugs found via screenshot review (see git history / commit notes), and full coverage of password reset + email verification (enumeration-proof forgot-password, single-use expiring tokens, real password change verified via login with old/new credentials).
A full HTTP smoke test (register → create doctor → check availability → hold → confirm → attempted double-book → graceful AI failure) was run end-to-end against a running instance of the API, as was the complete forgot-password and email-verification flow.
All three email types from the spec are implemented: booking confirmation, upcoming-appointment reminder (scheduled 24h before start, re-timed on reschedule, cancelled if the appointment is cancelled), and cancellation — each independently retried per recipient. Password-reset and email-verification emails are separate, transactional sends through the same pluggable EmailService.
The patient-facing reschedule flow, the doctor's RAG-backed "relevant patient history" view, and forgot-password/verify-email pages are all wired end-to-end in the UI, not just the API.
Frontend type-checks cleanly (tsc -b) and builds for production (vite build).
Not yet done by me: deploying to a public host, and obtaining real Groq/Google/SendGrid credentials — those require accounts only you can create. Everything is wired to work the moment real keys are in .env.
Tech stack
Frontend: React + Vite + TypeScript + React Router + Axios + Tailwind CSS
Backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL + JWT auth
Background jobs: Redis + Celery (worker + beat)
AI: Groq (openai/gpt-oss-20b by default, configurable)
RAG: ChromaDB
Email: pluggable (console/SendGrid/Mailgun)
Calendar: Google Calendar API, OAuth 2.0
Project structure
healthcare-appointment-manager/
├── frontend/           React app (patient/doctor/admin portals, chatbot)
├── backend/
│   ├── app/
│   │   ├── main.py         FastAPI entrypoint
│   │   ├── core/            config, db, security, auth deps
│   │   ├── models/           SQLAlchemy models
│   │   ├── schemas/          Pydantic request/response + AI schemas
│   │   ├── api/               route handlers
│   │   ├── services/         business logic (booking, slots, AI, RAG, email, calendar, chatbot)
│   │   ├── workers/           Celery tasks (email, calendar, reminders, RAG indexing, hold cleanup)
│   │   ├── prompts/           Groq prompt templates
│   │   └── utils/             interval math, time utils
│   ├── alembic/               migrations
│   ├── tests/                 pytest suite incl. concurrency test
│   ├── scripts/seed.py        synthetic demo data
│   └── .env.example
├── docker-compose.yml
├── README.md
└── SYSTEM_DESIGN.md
Quickstart (Docker)
cp backend/.env.example backend/.env
# fill in GROQ_API_KEY, GOOGLE_CLIENT_ID/SECRET, EMAIL_API_KEY as you get them
docker compose up --build
Frontend: http://localhost
Backend: http://localhost:8000 (docs at /docs)
The backend container runs alembic upgrade head automatically on startup.
Seed demo data (after containers are up):

docker compose exec backend python -m scripts.seed
Quickstart (local, no Docker)
Requires Python 3.12+, Node 20+, PostgreSQL, Redis.

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL etc.
alembic upgrade head
python -m scripts.seed          # optional demo data
uvicorn app.main:app --reload

# In separate terminals:
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info

# Frontend
cd frontend
npm install
npm run dev   # http://localhost:5173, proxies /api to :8000
Environment variables
See backend/.env.example for the full list with comments. Required for full functionality: DATABASE_URL, JWT_SECRET, GROQ_API_KEY, GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET, EMAIL_PROVIDER/EMAIL_API_KEY. The app runs and degrades gracefully without the AI/email/calendar keys (AI summaries show status: FAILED, email defaults to console logging, calendar sync is skipped per-user until they connect).

Database
Schema is defined in app/models/, migrations in alembic/versions/. Key design point: appointments has a partial unique index on (doctor_id, start_time) for active statuses — the actual double-booking guarantee (see SYSTEM_DESIGN.md). Run alembic revision --autogenerate -m "..." after model changes, review the generated migration, then alembic upgrade head.

Database schema (summary)
Full definitions in app/models/; migrations in alembic/versions/.

Table	Purpose	Key constraint
users	login identity + role (PATIENT/DOCTOR/ADMIN) + email verification flag	unique email
password_reset_tokens, email_verification_tokens	single-use, expiring, SHA-256-hashed tokens for forgot-password / verify-email	unique token_hash
patients, doctors	role-specific profile, 1:1 with users	
doctor_working_hours	per-weekday availability window	unique (doctor_id, day_of_week)
doctor_leaves	dates a doctor is unavailable	unique (doctor_id, leave_date)
appointments	the booking itself	unique (doctor_id, start_time) where status is active — the double-booking guarantee
slot_holds	temporary reservation while a patient fills the symptom form	indexed (doctor_id, start_time), (expires_at, status)
symptoms	patient-submitted symptom text	1:1 with appointments
pre_visit_ai_summaries, post_visit_ai_summaries	Groq output + status (PENDING/SUCCESS/FAILED)	
clinical_notes, prescriptions	doctor-entered consultation data	
medication_reminders	scheduled reminder sends derived from prescription frequency	indexed (status, scheduled_at)
notifications	per-recipient email queue (booking/reminder/cancellation/reschedule/leave-conflict)	indexed (status, scheduled_at)
calendar_events	per-user (patient or doctor) Google Calendar sync state	indexed (appointment_id, user_id)
chat_sessions, chat_messages	chatbot conversation history	
patient_history_documents	durable mirror of what's indexed into ChromaDB	indexed patient_id
password_reset_tokens, email_verification_tokens	single-use, expiring, hashed tokens for forgot-password and email verification	unique token_hash
API endpoints (summary)
Full interactive docs at /docs. Error responses: {"error": {"code": "...", "message": "..."}}.

Area	Endpoints
Auth	POST /api/auth/register, /login, /logout, GET /me, POST /forgot-password, POST /reset-password, POST /verify-email, POST /resend-verification
Doctors	GET /api/doctors, GET /{id}, GET /{id}/availability, POST /api/doctors (admin), PUT /{id} (admin), DELETE /{id} (admin)
Leave	POST /api/doctors/{id}/leave, DELETE /{id}/leave/{leave_id} (admin)
Slots	POST /api/slots/hold, DELETE /api/slots/{hold_id}
Appointments	POST /api/appointments/confirm/{hold_id}, GET /api/appointments, GET /{id}, PUT /{id}/reschedule, POST /{id}/cancel, GET /{id}/previsit-summary
Consultation	POST /api/appointments/{id}/clinical-notes, POST /{id}/prescription, GET /{id}/postvisit-summary, GET /{id}/relevant-history (doctor, RAG)
Chat	POST /api/chat/sessions, GET /api/chat/sessions, POST /api/chat/sessions/{id}/messages
History	GET /api/patients/me/history, GET /api/patients/me/history/relevant
Calendar	POST /api/calendar/connect, GET /api/calendar/callback
Google Calendar setup
In Google Cloud Console, create a project and enable the Google Calendar API.
Create OAuth 2.0 credentials (Web application type).
Add http://localhost:8000/api/calendar/callback (or your deployed URL) as an authorized redirect URI.
Put the client ID/secret in .env.
Users connect via POST /api/calendar/connect, which returns a consent URL; Google redirects back to /api/calendar/callback.
LLM prompts
See app/prompts/clinical_prompts.py. Pre-visit prompt requests urgency (Low/Medium/High), chief complaint, and three suggested questions as strict JSON. Post-visit prompt converts clinical notes + prescription into a patient-friendly summary, medication schedule, and follow-up steps — validated with Pydantic (app/schemas/ai.py); any failure or schema mismatch marks the row FAILED without fabricating data.

Testing
cd backend
pytest tests/ -v
Covers: auth/RBAC, slot generation (working hours, booked/held exclusion, leave), slot hold expiry and ownership, leave-conflict marking + notification, AI graceful degradation, and the concurrency acceptance test. Requires a running Postgres pointed to by DATABASE_URL (the partial unique index behavior is Postgres-specific; SQLite is not used for tests).

API documentation
Interactive docs are auto-generated by FastAPI at /docs (Swagger) and /redoc once the backend is running. Error responses use {"error": {"code": ..., "message": ...}} with standard HTTP status codes (400/401/403/404/409/429/500/503).

Troubleshooting
connection to server ... failed: Postgres isn't running or DATABASE_URL is wrong.
AI summaries always FAILED: check GROQ_API_KEY is set and valid; check backend logs for the underlying Groq error.
Calendar events never sync: the user hasn't completed /api/calendar/connect yet, or GOOGLE_CLIENT_ID/SECRET are unset — this fails silently by design (calendar is never on the booking critical path).
Emails not arriving: default EMAIL_PROVIDER=console only logs to stdout; set sendgrid and EMAIL_API_KEY for real delivery.

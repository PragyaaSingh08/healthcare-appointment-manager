# Healthcare Appointment & Follow-up Manager

A comprehensive clinic platform with dedicated portals for patients, doctors, and administrators. Features concurrency-safe slot holds, multi-layer double-booking prevention, Groq AI pre-visit and post-visit summaries, ChromaDB patient-history RAG, an AI assistant chatbot, multi-channel notifications, and Google Calendar two-way synchronization.

### Documentation Index

- [`SYSTEM_DESIGN.md`](./SYSTEM_DESIGN.md): Architecture overview, multi-layered concurrency control, slot holds, leave conflicts, and failure handling.
- [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md): Complete database schema specifications, table constraints, indexes, and ER diagram.
- [`LLM_PROMPTS.md`](./LLM_PROMPTS.md): AI prompt templates, schema definitions, validation rules, and fallback mechanisms.
- [`GOOGLE_CALENDAR_SETUP.md`](./GOOGLE_CALENDAR_SETUP.md): Step-by-step Google Cloud OAuth configuration and calendar sync lifecycles.
- [`DEPLOYMENT_GUIDE.md`](./DEPLOYMENT_GUIDE.md): Production deployment handbook for Railway (backend/database/worker) and Vercel (frontend).

---

## Live Deployment URLs

- **Frontend Application (Vercel)**: [https://healthcare-appointment-manager.vercel.app](https://healthcare-appointment-manager-xi.vercel.app)
- **Backend API (Railway)**: [https://healthcare-appointment-manager-production-831c.up.railway.app](https://healthcare-appointment-manager-production-831c.up.railway.app)
- **Interactive API Docs (Swagger UI)**: [https://healthcare-appointment-manager-production-831c.up.railway.app/docs](https://healthcare-appointment-manager-production-831c.up.railway.app/docs)
- **ReDoc Specification**: [https://healthcare-appointment-manager-production-831c.up.railway.app/redoc](https://healthcare-appointment-manager-production-831c.up.railway.app/redoc)


## Status of this Build

- **Backend Tests**: 34/34 unit and concurrency tests pass, including live PostgreSQL multi-threaded race conditions (12 concurrent threads targeting the same slot -> exactly 1 booking success, 11 conflicts, 1 database row).
- **Authentication & RBAC**: Stateless JWT auth with role isolation for `PATIENT`, `DOCTOR`, and `ADMIN`. Includes secure password reset and email verification flows.
- **Slot Hold Mechanism**: 300s TTL advisory hold with visual countdown timer in the frontend, inline expiration validation, and automated Celery Beat cleanup sweep every 60s.
- **Double-Booking Guarantee**: PostgreSQL partial unique index `uq_active_doctor_slot` on `(doctor_id, start_time) WHERE status IN ('SCHEDULED', 'RESCHEDULED')` coupled with `SELECT ... FOR UPDATE` row-level locking.
- **AI Clinical Decision Support**: Groq-powered pre-visit intake summaries (urgency level, chief complaint, suggested questions) and post-visit patient summaries (summary, medication schedule, follow-up steps) validated with strict Pydantic schemas.
- **Google Calendar Integration**: Complete OAuth 2.0 connect flow, callback handling, and background Celery workers syncing create, update (reschedule), and delete (cancellation) events for both patients and doctors.
- **Admin Doctor & Leave Management**: Complete administrative controls for doctor profile creation, editing, active/deactivated status toggling, and leave scheduling with conflict detection.
- **Frontend App**: Responsive React + Vite + TypeScript application styled with Tailwind CSS.

---

## Tech Stack

- **Frontend**: React 18, Vite, TypeScript, React Router 6, Axios, Tailwind CSS
- **Backend**: FastAPI (Python 3.12+), SQLAlchemy 2.0, Alembic, PostgreSQL, JWT (python-jose / passlib)
- **Asynchronous Processing**: Redis, Celery (Worker + Beat scheduler)
- **AI & RAG**: Groq API (`openai/gpt-oss-20b`), ChromaDB vector store
- **Email Delivery**: Pluggable provider system (Console / SendGrid / Mailgun)
- **Calendar Synchronization**: Google Calendar API v3 with OAuth 2.0

---

## Project Structure

```
healthcare-appointment-manager/
├── frontend/                     # React + Vite application
│   ├── src/
│   │   ├── components/           # Reusable UI (StatusBadge, Toast, CalendarConnectButton)
│   │   ├── context/              # AuthContext (JWT state & RBAC)
│   │   ├── layouts/              # AppLayout (navigation, role-based menus)
│   │   ├── pages/
│   │   │   ├── admin/            # AdminOverview, AdminDoctors (CRUD + leaves)
│   │   │   ├── doctor/           # DoctorAppointmentList, ConsultationView
│   │   │   ├── patient/          # Dashboard, DoctorSearch, DoctorProfile, AppointmentDetail, ChatAssistant
│   │   │   ├── CalendarCallback  # OAuth return handler
│   │   │   └── Login, Register, ForgotPassword, ResetPassword, VerifyEmail
│   │   ├── services/api.ts       # Axios client & API endpoints
│   │   └── types/                # TypeScript interface models
│   ├── .env.example
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── api/                  # Route handlers (auth, doctors, appointments, consultation, leave, calendar, chat)
│   │   ├── core/                 # Config, database engine, dependency injection
│   │   ├── models/               # SQLAlchemy ORM models & table constraints
│   │   ├── schemas/              # Pydantic validation & response models
│   │   ├── services/             # Business logic (booking, holds, AI, RAG, calendar, email, reminders)
│   │   ├── workers/              # Celery background tasks (email, calendar, reminders, hold cleanup, RAG)
│   │   ├── prompts/              # LLM prompt templates
│   │   └── utils/                # Time & interval algorithms
│   ├── alembic/                  # Database migrations
│   ├── tests/                    # Pytest test suite (concurrency, auth, slots, AI)
│   ├── scripts/seed.py           # Synthetic seed data generator
│   └── .env.example
├── docker-compose.yml
├── README.md
└── SYSTEM_DESIGN.md
```

---

## Google Calendar Integration Flow

1. **Initiating Connection**:
   - Patients and doctors can connect their Google Calendar directly from the sidebar or their respective dashboard widgets.
   - Clicking **"Connect Google Calendar"** sends a request to `POST /api/calendar/connect`, which builds a secure Google OAuth 2.0 authorization URL containing `client_id`, `redirect_uri`, offline access scope (`https://www.googleapis.com/auth/calendar.events`), and user state.
2. **Consent & Callback**:
   - The user authorizes access on Google's consent screen.
   - Google redirects the browser to the frontend `/calendar/callback?code=...&state=...` route.
   - [CalendarCallback.tsx](file:///d:/healthcare-appointment-manager%20%282%29/healthcare-appointment-manager/frontend/src/pages/CalendarCallback.tsx) exchanges the code for access/refresh tokens via `GET /api/calendar/callback`, securely stores them in the database (`google_oauth_tokens`), and returns the user to their dashboard with a confirmation state.
3. **Automated Event Sync**:
   - **On Booking**: `CalendarWorker` creates a calendar event on the primary calendar for both the patient and doctor independently.
   - **On Reschedule**: `CalendarWorker` issues an event patch updating the start and end time.
   - **On Cancellation**: `CalendarWorker` removes the calendar event.
   - **Fault Tolerance**: Calendar synchronization is processed asynchronously off the booking critical path. Temporary Google API rate limits or network issues retry with exponential backoff without affecting the database booking.

---

## Admin Doctor & Leave Management

Administrators have full operational control via the **Doctor Management** portal (`/admin/doctors`):

1. **Doctor Profiles**:
   - **Add Doctor**: Create doctor credentials, specialization, qualifications, years of experience, appointment slot duration (10–120 mins), and weekly working days.
   - **Edit Doctor**: Update clinical credentials, slot durations, or specialization at any time via the Edit modal.
   - **Deactivate / Reactivate**: Deactivating a doctor immediately hides them from patient searches and prevents new appointment bookings while preserving all existing appointment history.
2. **Doctor Leave & Conflict Management**:
   - **Schedule Leave**: Select a date and optional reason.
   - **Automated Conflict Transition**: Any existing active bookings for that doctor on the selected date are automatically transitioned to `RESCHEDULE_REQUIRED` status.
   - **Patient Notification**: Affected patients receive an automated conflict notification email with a direct link to reschedule into a new slot.
   - **Slot Recalculation**: The slot generation engine immediately marks that date unavailable.
   - **Delete Leave**: Administrators can cancel/delete a scheduled leave record when plans change.

---

## Quickstart (Docker)

```bash
cp backend/.env.example backend/.env
# Fill in GROQ_API_KEY, GOOGLE_CLIENT_ID/SECRET, EMAIL_API_KEY as needed
docker compose up --build
```

- Frontend: [http://localhost:5173](http://localhost:5173) (or http://localhost in production)
- Backend: [http://localhost:8000](http://localhost:8000) (Interactive Swagger docs at `/docs`)

Seed demo data:
```bash
docker compose exec backend python -m scripts.seed
```

---

## Quickstart (Local Development)

Requires Python 3.12+, Node 20+, PostgreSQL, Redis.

```bash
# Backend Setup
cd backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env   # Configure DATABASE_URL, JWT_SECRET, etc.
alembic upgrade head
python -m scripts.seed          # Optional synthetic demo data
uvicorn app.main:app --reload

# Start Celery Workers (in separate terminals)
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info

# Frontend Setup
cd frontend
npm install
cp .env.example .env   # Configure VITE_API_URL if connecting to remote backend
npm run dev            # http://localhost:5173
```

---

## Database Schema Overview

| Table | Purpose | Key Constraints |
|---|---|---|
| `users` | User identity & RBAC (`PATIENT`, `DOCTOR`, `ADMIN`) | Unique `email` |
| `patients`, `doctors` | Role profiles | 1:1 with `users` (`user_id`) |
| `doctor_working_hours` | Weekly schedule windows | Unique `(doctor_id, day_of_week)` |
| `doctor_leaves` | Doctor unavailable dates | Unique `(doctor_id, leave_date)` |
| `appointments` | Authoritative appointment bookings | **Partial Unique Index `(doctor_id, start_time)` where `status IN ('SCHEDULED', 'RESCHEDULED')`** |
| `slot_holds` | Temporary reservations during symptom intake | Indexed `(doctor_id, start_time)`, `(expires_at, status)` |
| `symptoms` | Patient-submitted pre-booking intake text | 1:1 with `appointments` |
| `pre_visit_ai_summaries` | LLM triage urgency, complaint, questions | 1:1 with `appointments` |
| `clinical_notes` | Doctor consultation notes | 1:1 with `appointments` |
| `prescriptions` | Structured medication items | Indexed `appointment_id` |
| `medication_reminders` | Scheduled patient medication alerts | Indexed `(status, scheduled_at)` |
| `post_visit_ai_summaries` | LLM patient-friendly summary & schedule | 1:1 with `appointments` |
| `notifications` | Independent email delivery queue | Indexed `(status, scheduled_at)` |
| `google_oauth_tokens` | Per-user OAuth credentials | Unique `user_id` |
| `calendar_events` | Calendar synchronization tracking | Indexed `(appointment_id, user_id)` |
| `patient_history_documents` | Durable mirror of ChromaDB RAG documents | Indexed `patient_id` |

---

## API Endpoints Summary

| Module | Endpoints |
|---|---|
| **Auth** | `POST /api/auth/register`, `POST /login`, `POST /logout`, `GET /me`, `POST /forgot-password`, `POST /reset-password`, `POST /verify-email`, `POST /resend-verification` |
| **Doctors** | `GET /api/doctors`, `GET /api/doctors/{id}`, `GET /api/doctors/{id}/availability`, `POST /api/doctors`, `PUT /api/doctors/{id}`, `DELETE /api/doctors/{id}` |
| **Leave** | `GET /api/doctors/{id}/leave`, `POST /api/doctors/{id}/leave`, `DELETE /api/doctors/{id}/leave/{leave_id}` |
| **Slots** | `POST /api/slots/hold`, `DELETE /api/slots/{hold_id}` |
| **Appointments** | `POST /api/appointments/confirm/{hold_id}`, `GET /api/appointments`, `GET /api/appointments/{id}`, `PUT /api/appointments/{id}/reschedule`, `POST /api/appointments/{id}/cancel`, `GET /api/appointments/{id}/previsit-summary` |
| **Consultation** | `GET /api/appointments/{id}/clinical-notes`, `POST /api/appointments/{id}/clinical-notes`, `GET /api/appointments/{id}/prescriptions`, `POST /api/appointments/{id}/prescription`, `GET /api/appointments/{id}/relevant-history`, `GET /api/appointments/{id}/postvisit-summary` |
| **Calendar** | `GET /api/calendar/status`, `POST /api/calendar/connect`, `GET /api/calendar/callback` |
| **Chat & RAG** | `POST /api/chat/sessions`, `GET /api/chat/sessions`, `POST /api/chat/sessions/{id}/messages`, `GET /api/patients/me/history/relevant` |

---

## LLM Prompts & Schemas

Defined in `app/prompts/clinical_prompts.py`:

- **Pre-Visit Triage Summary**:
  ```
  Analyse these symptoms and return: urgency level (Low / Medium / High), chief complaint, and three suggested questions for the doctor.
  ```
  *Validated with Pydantic (`PreVisitAIResult`). If the LLM call times out or fails schema validation, the appointment remains valid and `pre_visit_ai_summaries.status` is set to `FAILED` without fabricating hallucinated data.*

- **Post-Visit Patient Summary**:
  ```
  Convert these clinical notes into a patient-friendly summary with medication schedule and follow-up steps.
  ```
  *Validated with Pydantic (`PostVisitAIResult`), extracting patient-friendly instructions, structured medication timings, and follow-up precautions.*

---

## Google Calendar Setup Steps

1. In the [Google Cloud Console](https://console.cloud.google.com/), create a project and enable the **Google Calendar API**.
2. Create OAuth 2.0 credentials (Web application).
3. Add `http://localhost:5173/calendar/callback` (or your deployed URL `https://<your-domain>/calendar/callback`) and `http://localhost:8000/api/calendar/callback` to the authorized redirect URIs.
4. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`.
5. In the web app, click **"Connect Google Calendar"** to link your account.

---
## System Architecture Flow:
 <img width="1040" height="1459" alt="image" src="https://github.com/user-attachments/assets/669cf23d-5ad9-469a-a613-7ed1fd3cce5a" />


## Testing

```bash
cd backend
pytest tests/ -v
```

Test coverage includes:
- Concurrency acceptance test (12 simultaneous threads booking the identical doctor and time slot against live PostgreSQL).
- Role-based authorization & route protection.
- Slot generation respecting working hours, buffer duration, holds, and doctor leave dates.
- Slot hold expiration, manual release, and inline boundary checks.
- AI service graceful degradation on invalid JSON, schema mismatches, and timeouts.
- Password reset and email verification token lifecycles.

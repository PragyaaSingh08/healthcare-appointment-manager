# System Design — Healthcare Appointment & Follow-up Manager

## Architecture

React (Vite/TS) talks to a FastAPI **modular monolith** over REST. The API layer calls a service layer (booking, slots, AI, RAG, notifications, calendar), which is the only code with DB/external-API access. PostgreSQL is the source of truth; Redis backs Celery workers for everything off the critical path; ChromaDB holds vector embeddings for patient-history RAG, with Postgres keeping a durable metadata mirror of what was indexed. A modular monolith was chosen over microservices because the workload doesn't need independent scaling or deployment of its parts yet — service boundaries in the code (one module per concern) mean it can be split later without a rewrite.

## Double-booking prevention

Booking correctness is layered, not reliant on any single mechanism:

1. **Slot holds** (UX layer): selecting a slot creates a `SlotHold` (HELD → CONFIRMED/EXPIRED/RELEASED) with a configurable TTL (default 300s). This reduces contention but is not itself authoritative.
2. **Transactional re-check**: at confirmation, the service re-validates the hold (ownership, not expired), re-checks leave, and re-checks for conflicting active appointments for that doctor+time window, using `SELECT ... FOR UPDATE` on Postgres to serialize concurrent transactions targeting the same slot.
3. **Partial unique index** (the real guarantee): `UNIQUE (doctor_id, start_time) WHERE status IN ('SCHEDULED','RESCHEDULED')`. Even if two transactions race past step 2 under READ COMMITTED, the second `INSERT` raises an `IntegrityError`, which the service catches and converts into `409 SLOT_ALREADY_BOOKED`. This was verified with a real concurrency test: 12 threads, each with its own DB session, booking the identical doctor+slot against a live Postgres instance — exactly 1 succeeded, 11 got 409, and the database held exactly one active row.

## Slot hold mechanism

Holds prevent two patients from filling out the symptom form for the same slot simultaneously without either seeing a conflict until the last second. Expiry is checked in two places — inline during any new hold/booking attempt (so a stale hold can never block a slot indefinitely even if the cleanup worker is delayed) and via a scheduled `HoldCleanupWorker` sweep every 60s using an indexed `(expires_at, status)` query.

## Doctor leave conflict handling

Adding leave never deletes appointment history. It finds all active appointments on that date (indexed `doctor_id + leave_date` lookup), transitions them to `RESCHEDULE_REQUIRED` (a distinct status, not `CANCELLED`), and queues a `LEAVE_CONFLICT` notification per affected patient. New slot generation for that doctor+date returns empty once leave exists, checked before any candidate slots are generated.

## Notification failure handling

Every notification is a row scoped to one recipient (patient or doctor), so a patient email succeeding and a doctor email failing are tracked and retried completely independently — one never blocks or masks the other. Failures are typed: `EmailTransientError` (timeout/429/5xx) triggers exponential backoff up to `NOTIFICATION_MAX_ATTEMPTS`; `EmailPermanentError` (bad address, auth failure) fails immediately without wasting retries. The same pattern applies to Google Calendar sync (`CalendarTransientError`/`CalendarPermanentError`, `SYNC_PENDING` status, independent per-user rows) and medication reminders.

## Database consistency

Short, single-purpose transactions: DB writes commit before any external call (email/calendar/Groq) is queued — never inside the same transaction. This keeps the critical path (auth → validate → transact → commit) small and keeps external outages from blocking bookings.

## AI/RAG architecture

All Groq calls funnel through one `GroqService`, so model/timeout/retry config lives in one place (`GROQ_MODEL` env var only). Pre/post-visit outputs are requested as strict JSON and validated with Pydantic; on any failure (timeout, invalid JSON, schema violation) the row is marked `FAILED` and the appointment/symptoms remain fully valid — verified end-to-end with no Groq key configured. RAG retrieval always filters by `patient_id` via ChromaDB metadata before semantic search runs, so there is no code path capable of cross-patient retrieval; the chatbot's tools inject `patient_id` from the authenticated session, never from LLM output.

## External-service failure isolation

Every external integration (Groq, email, calendar) has typed transient/permanent errors, is called outside DB transactions, and degrades to a stored `FAILED`/`SYNC_PENDING` status rather than raising into the request path.

## Latency

Booking's critical path is auth → hold validation → transaction → commit; email, calendar, and RAG indexing are enqueued after commit. Slot generation avoids per-slot queries by fetching appointments and holds once (O(S+A+H)) and filtering in memory.

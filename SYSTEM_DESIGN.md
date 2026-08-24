# System Design Document

## Architecture Overview

The Healthcare Appointment & Follow-up Manager follows a three-tier architecture with clear separation between presentation, business logic, and data layers. The frontend is a React-based single-page application (SPA) with role-based routing for patients, doctors, and administrators. The backend is built with FastAPI, providing async REST endpoints with JWT authentication and role-based access control (RBAC). PostgreSQL serves as the primary database with SQLAlchemy ORM for data access, while Redis handles background job queuing and caching. External integrations include LLM APIs for AI summaries, email services for notifications, and Google Calendar API for event synchronization.

---

## Double Booking Prevention

The system implements a multi-layered approach to prevent double booking:

### Slot Locking

When a patient initiates booking, the system generates a unique `slot_token` and stores it in the appointments table with an expiry timestamp (default: 10 minutes). This token is checked during the final booking confirmation. If another user attempts to book the same slot, the token mismatch triggers a conflict error.

### Database Constraints

A unique constraint on `(doctor_id, appointment_date, appointment_time)` ensures that even if application logic fails, the database rejects duplicate bookings at the constraint level. This provides a safety net against race conditions.

### Transaction Isolation

All booking operations use database transactions with `SERIALIZABLE` isolation level. The booking flow:
1. Start transaction
2. Check slot availability with `SELECT ... FOR UPDATE`
3. Verify no conflicting appointments exist
4. Insert appointment record
5. Commit transaction

If any step fails, the entire transaction rolls back, preventing partial state.

### Optimistic Locking

For high-traffic scenarios, the system uses optimistic locking with version numbers. Each slot check includes a timestamp, and the final booking verifies the slot hasn't been taken since the initial check.

---

## Slot Hold Mechanism

### Temporary Reservation

When a patient selects a time slot, the system creates a temporary hold:
- Generate unique `slot_token` (UUID)
- Store in `appointments.slot_token` column
- Set `slot_token_expiry` to current time + 10 minutes
- Return token to frontend

### Expiration Strategy

A Celery background job runs every minute to:
1. Query appointments where `slot_token_expiry < NOW()` and `status = 'pending'`
2. Clear expired tokens
3. Release slots back to availability

This ensures slots aren't indefinitely held by abandoned booking sessions.

### Token Validation

During final booking confirmation, the system validates:
- Token exists and matches the appointment
- Token hasn't expired
- Appointment status is still 'pending'

Invalid tokens trigger a "Slot no longer available" error, prompting the patient to select a new time.

---

## Doctor Leave Conflict Handling

### Detection

When a doctor marks leave dates, the system:
1. Queries all confirmed appointments within the leave date range
2. Identifies affected patients
3. Calculates rescheduling options based on doctor's next available slots

### Notification

For each affected appointment:
1. Create notification record with type `doctor_leave`
2. Send email with rescheduling link
3. Update appointment status to `pending_reschedule`
4. Log notification attempt

### Rescheduling Flow

Patients receive an email with:
- Explanation of leave
- Direct link to reschedule page
- Suggested alternative slots
- Priority booking (bypass waitlist)

The reschedule page pre-fills the original appointment details and shows only available slots within a 14-day window.

### Admin Override

Administrators can:
- Bulk reschedule all affected appointments
- Assign to alternative doctors (with patient consent)
- Manually contact patients for complex cases

---

## Notification Reliability

### Background Jobs

All notifications are processed asynchronously via Celery:
1. Notification request creates a record in `notifications` table
2. Celery task picks up pending notifications
3. Email service API is called
4. Result logged in `notification_logs`

This decouples notification sending from the main request-response cycle.

### Retry Strategy

Failed notifications use exponential backoff:
- Attempt 1: Immediate
- Attempt 2: 5 minutes later
- Attempt 3: 30 minutes later
- Attempt 4: 2 hours later

After 4 failed attempts, the notification is marked as `failed` and flagged for manual review.

### Failure Handling

- **Transient Errors** (timeout, rate limit): Retry with backoff
- **Permanent Errors** (invalid email, account disabled): Mark as failed, notify admin
- **Partial Failures** (some recipients fail): Log individually, continue with others

### Monitoring

- Dashboard shows notification delivery rate
- Alerts trigger if failure rate exceeds 5%
- Daily reports list all failed notifications

---

## AI Failure Handling

### Timeout Handling

LLM calls have a 30-second timeout:
- If exceeded, the system catches the timeout exception
- Fallback summary is generated automatically
- User receives a message: "AI summary unavailable, displaying manual summary"

### Graceful Degradation

The system handles AI failures at multiple levels:
1. **Provider Failover**: If Groq fails, retry with OpenAI, then Anthropic
2. **Fallback Summaries**: Pre-defined templates for common scenarios
3. **Manual Entry**: Doctors can override AI summaries with their own notes

### Fallback Summaries

For pre-visit summaries:
```json
{
  "urgency": "Medium",
  "chief_complaint": "Patient-reported symptoms pending review",
  "suggested_questions": ["Please describe symptoms in detail", "When did symptoms start?", "Any medication taken?"],
  "is_fallback": true
}
```

For post-visit summaries:
```json
{
  "summary": "Please refer to your doctor's notes and prescription below.",
  "medication_schedule": ["See prescription details"],
  "follow_up_steps": ["Follow your doctor's instructions"],
  "is_fallback": true
}
```

### User Communication

- Patients see: "Your summary is being prepared"
- Doctors see: "AI summary unavailable, please review symptoms manually"
- Admins receive alerts for repeated failures

---

## Security

### JWT Authentication

- Tokens signed with RS256 (asymmetric)
- Access tokens expire in 60 minutes
- Refresh tokens expire in 7 days
- Tokens include user ID, role, and permissions

### RBAC (Role-Based Access Control)

Three roles with distinct permissions:
- **Patient**: Book appointments, view own records, submit symptoms
- **Doctor**: View schedule, submit notes, mark leave
- **Admin**: Manage users, view analytics, override bookings

Middleware checks role permissions on every request.

### Password Hashing

- Bcrypt with 12 rounds
- Salt automatically generated per password
- Passwords never stored in plain text

### Data Protection

- All API calls over HTTPS
- Sensitive data encrypted at rest (Google tokens, passwords)
- Input validation on all endpoints (Pydantic schemas)
- SQL injection prevention via parameterized queries

---

## Scalability Considerations

### Async Jobs

- Celery workers can be horizontally scaled
- Redis broker supports multiple workers
- Long-running tasks (AI summaries, email batches) don't block API

### Database Indexing

Critical indexes for performance:
- `appointments (doctor_id, appointment_date, appointment_time)` - Schedule queries
- `appointments (patient_id, created_at)` - Patient history
- `notifications (user_id, is_read, created_at)` - Notification list
- `medication_reminders (reminder_date, is_sent)` - Daily reminder jobs

### Connection Pooling

- SQLAlchemy async engine with pool_size=20
- Prevents connection exhaustion under load

### Future Scaling

1. **Horizontal Scaling**: Deploy multiple backend instances behind load balancer
2. **Database Sharding**: Partition by doctor_id or patient_id for large datasets
3. **Caching Layer**: Redis cache for frequently accessed data (doctor profiles, slots)
4. **CDN**: Serve static assets (images, CSS, JS) via CDN
5. **Microservices**: Separate AI, notifications, and calendar into independent services
6. **Queue Scaling**: Add more Celery workers based on queue depth monitoring

### Monitoring

- Prometheus metrics for API latency, error rates, queue depth
- Grafana dashboards for real-time visibility
- Alerts for high error rates, slow queries, queue backlog

---

## Trade-offs

1. **Slot Hold Duration**: 10 minutes balances user experience vs. slot availability
2. **AI Timeout**: 30 seconds prevents user frustration but may miss complex analyses
3. **Retry Attempts**: 4 retries balance reliability vs. cost
4. **Token Expiry**: Refresh tokens expire in 7 days for security vs. convenience

---

## Disaster Recovery

- Database backups daily (point-in-time recovery)
- Redis persistence enabled
- Email retry queue survives restarts
- LLM failures don't block core functionality

API Documentation — Healthcare Appointment & Follow-up Manager

Table of Contents
Authentication
Doctors
Appointments
AI Features
Notifications
Google Calendar

Admin
1. Authentication
1.1 Register Patient
Field	Detail
Endpoint	/auth/register
Method	POST
Purpose	Register a new patient account (per README §7 — "Register a new patient account")
Authentication	Public — no token required
Parameters	None
Request Body	Not Specified in Source Material (source confirms this creates a patient account; exact fields such as name/email/password are not enumerated in the PDF or README)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material (typically 201 Created, unconfirmed)
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
1.2 Login
Field	Detail
Endpoint	/auth/login
Method	POST
Purpose	Authenticate a user and issue JWT access/refresh tokens (per README §7)
Authentication	Public — no token required
Parameters	None
Request Body	Not Specified in Source Material (credentials expected, exact field names not confirmed)
Response Body	Not Specified in Source Material (README confirms "returns JWT access/refresh tokens" but does not specify field names)
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
1.3 Refresh Token
Field	Detail
Endpoint	/auth/refresh
Method	POST
Purpose	Refresh an expired access token (per README §7)
Authentication	Authenticated (valid refresh token required)
Parameters	None
Request Body	Not Specified in Source Material
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material

Role-based auth confirmed in source: The PDF brief explicitly requires "role-based auth (patient / doctor / admin)" (Technical Expectations). The README's Security section (§15) confirms JWT authentication, bcrypt password hashing, and role-based access control as implemented mechanisms, but does not specify token payload structure, expiry duration, or error codes.

2. Doctors
2.1 Search Doctors
Field	Detail
Endpoint	/doctors?specialization=
Method	GET
Purpose	Search doctors by specialization (per PDF: "search doctors by specialisation"; README §7 confirms this endpoint)
Authentication	Patient
Parameters	Query parameter: specialization (Not Specified in Source Material whether additional filters such as availability or rating exist as query params — README feature list mentions "availability, and rating" as searchable but the endpoint signature only documents specialization)
Request Body	None (GET request)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
2.2 Get Doctor's Available Slots
Field	Detail
Endpoint	/doctors/{id}/slots
Method	GET
Purpose	Retrieve available appointment slots for a given doctor (per README §7)
Authentication	Patient
Parameters	Path parameter: id (doctor ID)
Request Body	None (GET request)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
2.3 Doctor Schedule View
Field	Detail
Endpoint	/doctor/appointments
Method	GET
Purpose	View the logged-in doctor's schedule (per README §7)
Authentication	Doctor
Parameters	None specified
Request Body	None (GET request)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
2.4 Mark Doctor Leave
Field	Detail
Endpoint	/doctor/leave
Method	POST
Purpose	Mark a leave day for the doctor. Per the PDF brief: "When a doctor is marked on leave for a date with existing bookings, affected patients must be notified."
Authentication	Doctor
Parameters	None specified
Request Body	Not Specified in Source Material (a leave date is required per the PDF's functional description, but the exact field name/format is not documented)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
Confirmed side effect	Per PDF brief, marking leave on a date with existing bookings must trigger patient notification. The exact notification endpoint/mechanism triggered is not documented — see Section 5, Notifications.
3. Appointments
3.1 Place Slot Hold
Field	Detail
Endpoint	/appointments/hold
Method	POST
Purpose	Temporarily reserve a slot for 5 minutes while the patient completes booking (per README §7, §14 — "Slot Hold Mechanism")
Authentication	Patient
Parameters	None specified
Request Body	Not Specified in Source Material (doctor ID and desired slot time are implied by the feature description but not documented as fields)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material (README §14 confirms conflicting holds are prevented via unique constraint on (doctor_id, slot_start), but does not specify the HTTP error code returned)
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
3.2 Confirm Appointment
Field	Detail
Endpoint	/appointments/confirm
Method	POST
Purpose	Convert an active slot hold into a confirmed booking (per README §7)
Authentication	Patient
Parameters	None specified
Request Body	Not Specified in Source Material
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
Confirmed side effects	Per PDF brief: booking confirmation triggers email notification to patient and doctor, and Google Calendar event creation for both. See Section 5 and Section 6.
3.3 Submit Pre-Visit Symptoms
Field	Detail
Endpoint	/appointments/{id}/symptoms
Method	POST
Purpose	Submit the pre-visit symptom form used to generate the AI pre-visit summary (per PDF: "Patient fills a symptom form before confirming"; README §7)
Authentication	Patient
Parameters	Path parameter: id (appointment ID)
Request Body	Not Specified in Source Material (a free-text or structured symptoms field is implied by the PDF's LLM prompt template — "Symptoms: <symptoms>" — but the exact request schema is not documented)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material (PDF requires "LLM failures must be handled gracefully" — no specific error code documented)
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
3.4 Reschedule Appointment
Field	Detail
Endpoint	/appointments/{id}/reschedule
Method	PATCH
Purpose	Reschedule an existing appointment (per README §7)
Authentication	Patient
Parameters	Path parameter: id (appointment ID)
Request Body	Not Specified in Source Material
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
Confirmed side effects	Per PDF brief: reschedule must update the associated Google Calendar event (not create a duplicate) and trigger notification.
3.5 Cancel Appointment
Field	Detail
Endpoint	/appointments/{id}
Method	DELETE
Purpose	Cancel an appointment (per README §7)
Authentication	Patient
Parameters	Path parameter: id (appointment ID)
Request Body	None specified
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
Confirmed side effects	Per PDF brief: cancellation triggers an email notification to both parties and deletes the linked Google Calendar event.
3.6 Get Post-Visit Summary
Field	Detail
Endpoint	/appointments/{id}/summary
Method	GET
Purpose	Retrieve the AI-generated, patient-friendly post-visit summary (per PDF: "produce a patient-friendly summary after the visit"; README §7)
Authentication	Patient
Parameters	Path parameter: id (appointment ID)
Request Body	None (GET request)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
3.7 Submit Consultation Notes & Prescription
Field	Detail
Endpoint	/doctor/consultations
Method	POST
Purpose	Doctor submits post-visit clinical notes and prescription, which are converted into a patient-friendly summary (per PDF: "Doctor submits post-visit notes and prescription; LLM generates a patient-friendly post-visit summary"; README §7)
Authentication	Doctor
Parameters	None specified
Request Body	Not Specified in Source Material (clinical notes and prescription data are implied by the LLM prompt template — "Convert these clinical notes..." — but exact field structure, e.g. drug name/dosage/frequency breakdown, is not documented at the API layer)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
Confirmed side effect	Per PDF brief: "System sends medication reminders based on prescription frequency" — triggered off this submission.
4. AI Features

These are not documented as standalone REST endpoints in the source material — the PDF and README describe them as LLM-integration behaviors invoked internally by the Appointments/Consultations endpoints above (§3.3 and §3.7), not as endpoints a client calls directly. They are listed separately here per the requested documentation structure, since the source material specifies their prompts and purpose explicitly even though it does not expose them as independent routes.

4.1 Pre-Visit Symptom Summary (AI)
Field	Detail
Endpoint	Not exposed as a standalone endpoint in source material — invoked internally by POST /appointments/{id}/symptoms
Method	N/A (internal LLM call)
Purpose	Analyze submitted symptoms and generate: urgency level (Low/Medium/High), chief complaint, and three suggested questions for the doctor (per PDF, "LLM Usage Guidance" section, verbatim prompt template)
Authentication	N/A — invoked server-side by an authenticated patient request
Parameters	N/A
Request Body (LLM prompt)	"Analyse these symptoms and return: urgency level (Low / Medium / High), chief complaint, and three suggested questions for the doctor. Symptoms: <symptoms>" — exact prompt as specified in the PDF
Response Body	Not Specified in Source Material (PDF specifies the fields the output should contain — urgency level, chief complaint, three questions — but not a formal JSON schema)
Success Responses	Not Specified in Source Material
Error Responses	Per README §8: on LLM failure, a fallback payload is returned (urgency: "Unknown", generic message) so the flow does not block. Exact HTTP status codes are not specified.
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
4.2 Post-Visit Patient Summary (AI)
Field	Detail
Endpoint	Not exposed as a standalone endpoint in source material — invoked internally by POST /doctor/consultations
Method	N/A (internal LLM call)
Purpose	Convert clinical notes into a patient-friendly summary with medication schedule and follow-up steps (per PDF, "LLM Usage Guidance" section, verbatim prompt template)
Authentication	N/A — invoked server-side by an authenticated doctor request
Parameters	N/A
Request Body (LLM prompt)	"Convert these clinical notes into a patient-friendly summary with medication schedule and follow-up steps: <notes>" — exact prompt as specified in the PDF
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material (README §8 confirms graceful fallback behavior generally applies, exact error format not documented)
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
4.3 RAG Medical History Retrieval
Field	Detail
Endpoint	/doctor/patients/{id}/history
Method	GET
Purpose	Retrieve relevant past-visit context for a patient via ChromaDB semantic search (per README §7, §8)
Authentication	Doctor
Parameters	Path parameter: id (patient ID)
Request Body	None (GET request)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material

Note: The PDF brief itself does not mention RAG or ChromaDB — this feature and its endpoint originate only from the README (which was authored from the user's stated tech stack), not from the original project brief.

5. Notifications
5.1 View Notification Delivery Status
Field	Detail
Endpoint	/admin/notifications
Method	GET
Purpose	View notification delivery status system-wide (per README §7)
Authentication	Admin
Parameters	None specified
Request Body	None (GET request)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material

No patient/doctor-facing notification endpoint is documented. Per the PDF brief, notifications are triggered as side effects of other actions (booking, reminder, cancellation) rather than pulled via a dedicated client-facing route:

"Email notifications to both patient and doctor: booking confirmation, reminder, cancellation" (PDF, Scope of Work)
"System sends medication reminders based on prescription frequency" (PDF, Scope of Work)
"Background job for medication reminders and email retries" (PDF, Technical Expectations)

These are implemented via the Email Worker and Reminder Worker described in README §13, not as REST endpoints. No endpoint path for triggering or listing a single user's notifications is present in the source material.

6. Google Calendar
6.1 Start OAuth Flow
Field	Detail
Endpoint	/calendar/oauth/start
Method	GET
Purpose	Begin Google OAuth 2.0 authorization so the platform can create/update/delete calendar events on the user's behalf (per README §7, §9)
Authentication	Patient/Doctor
Parameters	None specified
Request Body	None (GET request)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
6.2 OAuth Callback
Field	Detail
Endpoint	/calendar/oauth/callback
Method	GET
Purpose	Handles the Google OAuth redirect, exchanges authorization code for access/refresh tokens (per README §7, §9)
Authentication	Patient/Doctor (session context from OAuth redirect)
Parameters	Query parameters set by Google's OAuth redirect (e.g., authorization code) — exact parameter names Not Specified in Source Material
Request Body	None (GET request)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material

Calendar event creation/update/deletion is not exposed as a direct client-callable endpoint in the source material. Per PDF brief ("Google Calendar event created for both on booking; updated or deleted on reschedule or cancellation") and README §9/§13, these operations are performed internally by the Calendar Worker as a side effect of the Appointments endpoints (§3.2, §3.4, §3.5), not via dedicated /calendar/events routes.

7. Admin
7.1 Create Doctor Profile
Field	Detail
Endpoint	/admin/doctors
Method	POST
Purpose	Create a doctor profile — specialization, working hours, slot duration (per PDF: "Admin creates and manages doctor profiles"; README §7)
Authentication	Admin
Parameters	None specified
Request Body	Not Specified in Source Material (PDF names the relevant profile attributes — specialisation, working hours, slot duration, leave days — but does not define a formal request schema)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
7.2 Update Doctor Profile
Field	Detail
Endpoint	/admin/doctors/{id}
Method	PATCH
Purpose	Update a doctor profile / working hours (per README §7)
Authentication	Admin
Parameters	Path parameter: id (doctor ID)
Request Body	Not Specified in Source Material
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
7.3 View Audit Logs
Field	Detail
Endpoint	/admin/audit-logs
Method	GET
Purpose	View system-wide audit trail (per README §7)
Authentication	Admin
Parameters	None specified
Request Body	None (GET request)
Response Body	Not Specified in Source Material
Success Responses	Not Specified in Source Material
Error Responses	Not Specified in Source Material
Example Request	Not Specified in Source Material
Example Response	Not Specified in Source Material
Appendix A — Endpoints Referenced Only as Behaviors, Not Routes

The following capabilities are explicitly required by the PDF brief but are not given a documented endpoint path in either the PDF or README. They are listed here for completeness and traceability, per the instruction not to assume undocumented endpoints:

Capability	Source Reference	Documented Endpoint?
Double-booking prevention on simultaneous requests	PDF, Scope of Work: "System must prevent double-booking and handle simultaneous booking attempts safely"	No — implemented via DB-level locking/constraints (README §14), not a distinct route
Notify patients when a doctor goes on leave with existing bookings	PDF, Scope of Work	No — described as a side effect of /doctor/leave (§2.4), no dedicated notification-trigger route documented
Email retry on failure	PDF, Technical Expectations: "Background job for medication reminders and email retries"	No — implemented by the Email Worker (README §13), not a callable endpoint
Google Calendar OAuth setup steps	PDF, Deliverables: "README with ... Google Calendar setup steps"	Partially — OAuth start/callback routes documented in §6; the setup process itself is deployment configuration, not an API route
Document Notes
All endpoint paths in this document are taken directly from the API Documentation table in README.md §7, which was generated from the user-provided project specification. No endpoint has been added beyond what is listed there or explicitly implied by feature descriptions in the original PDF brief.
Request/response JSON schemas, field names, and HTTP status codes are not defined anywhere in the source material (PDF or README). Marking them as "Not Specified in Source Material" throughout is intentional and should not be treated as an omission — it reflects the actual state of the available documentation.
For binding request/response contracts, the authoritative source once implemented will be the live OpenAPI schema exposed at /docs (per README §10).

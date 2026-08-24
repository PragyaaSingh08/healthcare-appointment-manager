# Google Calendar Integration Setup

This guide walks through setting up Google Calendar API integration for the Healthcare Appointment System.

---

## Create Google Cloud Project

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: `healthcare-appointment-system`
4. Click "Create"
5. Wait for project creation (30 seconds)

---

## Enable Google Calendar API

1. In the Cloud Console, ensure your project is selected
2. Navigate to **APIs & Services** → **Library**
3. Search for "Google Calendar API"
4. Click on "Google Calendar API"
5. Click "Enable"
6. Wait for API to be enabled (green checkmark)

---

## Create OAuth Credentials

1. Navigate to **APIs & Services** → **Credentials**
2. Click "+ CREATE CREDENTIALS" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - **User Type**: External
   - **App Name**: Healthcare Appointment System
   - **User Support Email**: Your email
   - **Developer Contact**: Your email
   - Click "Save and Continue"
4. **Scopes**: Click "Save and Continue" (no additional scopes needed)
5. **Test Users**: Add your email as a test user, click "Save and Continue"
6. Back to credentials, select:
   - **Application Type**: Web application
   - **Name**: `healthcare-calendar-client`
7. Under "Authorized redirect URIs":
   - Click "+ ADD URI"
   - Add: `http://localhost:8000/api/v1/calendar/callback` (development)
   - Add: `https://your-production-domain.com/api/v1/calendar/callback` (production)
8. Click "Create"
9. Copy the **Client ID** and **Client Secret**

---

## Configure Redirect URIs

Ensure the redirect URI matches exactly between:
- Google Cloud Console credentials
- Backend `.env` file (`GOOGLE_REDIRECT_URI`)
- Frontend OAuth initiation

**Development:**
```text
http://localhost:8000/api/v1/calendar/callback
```

**Production:**
```text
https://api.yourdomain.com/api/v1/calendar/callback
```

---

## Environment Variables

Add the following to your backend `.env` file:

```env
# Google Calendar OAuth
GOOGLE_CLIENT_ID=xxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/calendar/callback
GOOGLE_SCOPES=https://www.googleapis.com/auth/calendar.events

# Frontend (for OAuth initiation)
NEXT_PUBLIC_GOOGLE_CLIENT_ID=xxxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com
```

---

## Authentication Flow

### Step 1: User Initiates Connection

Frontend calls:
```text
GET /api/v1/calendar/connect
```

Backend responds with Google OAuth URL:
```text
https://accounts.google.com/o/oauth2/v2/auth?
client_id={GOOGLE_CLIENT_ID}&
redirect_uri={GOOGLE_REDIRECT_URI}&
response_type=code&
scope=https://www.googleapis.com/auth/calendar.events&
state={csrf_token}&
access_type=offline&
prompt=consent
```

### Step 2: User Consents

- User is redirected to Google consent screen
- User grants calendar access
- Google redirects back to `GOOGLE_REDIRECT_URI` with `code` and `state`

### Step 3: Token Exchange

Backend receives callback:
```text
GET /api/v1/calendar/callback?code={authorization_code}&state={csrf_token}
```

Backend:
1. Validates `state` against CSRF token
2. Exchanges code for tokens:
```python
token_response = google_oauth.exchange_code(code)
```
3. Stores tokens in database:
   - `google_calendar_token`: Access token (encrypted)
   - `google_calendar_token_expiry`: Expiration timestamp
   - `google_calendar_connected`: true

### Step 4: Store Refresh Token

- Save refresh token for long-term access
- Use refresh token to get new access tokens when expired

---

## Event Creation Flow

### When Appointment is Booked

1. **Check Connection**: Verify user has connected Google Calendar
2. **Get Access Token**: Refresh if expired
3. **Create Event**:
```python
event = {
    'summary': f'Appointment with Dr. {doctor_name}',
    'description': f'Patient: {patient_name}\nSymptoms: {symptoms}',
    'start': {
        'dateTime': f'{appointment_date}T{appointment_time}:00',
        'timeZone': 'UTC',
    },
    'end': {
        'dateTime': f'{appointment_date}T{end_time}:00',
        'timeZone': 'UTC',
    },
    'attendees': [
        {'email': patient_email},
        {'email': doctor_email},
    ],
    'reminders': {
        'useDefault': False,
        'overrides': [
            {'method': 'email', 'minutes': 24 * 60},
            {'method': 'popup', 'minutes': 60},
        ],
    },
}

created_event = service.events().insert(
    calendarId='primary',
    body=event
).execute()
```
4. **Store Event ID**: Save `created_event['id']` in `appointments.calendar_event_id`
5. **Send Confirmations**: Google sends email invitations to attendees

---

## Event Update Flow

### When Appointment is Rescheduled

1. **Get Event ID**: Retrieve from `appointments.calendar_event_id`
2. **Update Event**:
```python
updated_event = {
    'summary': f'Appointment with Dr. {doctor_name}',
    'start': {
        'dateTime': f'{new_date}T{new_time}:00',
        'timeZone': 'UTC',
    },
    'end': {
        'dateTime': f'{new_date}T{new_end_time}:00',
        'timeZone': 'UTC',
    },
}

service.events().update(
    calendarId='primary',
    eventId=calendar_event_id,
    body=updated_event
).execute()
```
3. **Notify Attendees**: Google sends update notifications

---

## Event Cancellation Flow

### When Appointment is Cancelled

1. **Get Event ID**: Retrieve from `appointments.calendar_event_id`
2. **Delete Event**:
```python
service.events().delete(
    calendarId='primary',
    eventId=calendar_event_id
).execute()
```
3. **Notify Attendees**: Google sends cancellation notifications

---

## Troubleshooting

### Error: `redirect_uri_mismatch`

**Cause**: Redirect URI in Google Console doesn't match the one in the request

**Solution**:
1. Verify exact match (including http/https, trailing slash)
2. Add both development and production URIs to Google Console
3. Check for URL encoding issues

---

### Error: `invalid_grant`

**Cause**: Authorization code expired or already used

**Solution**:
1. Codes expire in 10 minutes
2. Codes can only be used once
3. Re-initiate OAuth flow if code is invalid

---

### Error: `insufficient_permission`

**Cause**: User hasn't granted calendar access

**Solution**:
1. Ensure `scope` includes `https://www.googleapis.com/auth/calendar.events`
2. Re-authorize with `prompt=consent`
3. Check user's Google Account permissions

---

### Error: `Token has been expired or revoked`

**Cause**: Access token expired or user revoked access

**Solution**:
1. Use refresh token to get new access token
2. If refresh fails, prompt user to re-authorize
3. Set `google_calendar_connected = false` in database

---

### Error: `Calendar not found`

**Cause**: User doesn't have a Google Calendar

**Solution**:
1. All Google accounts have a default calendar
2. Use `calendarId='primary'` for default calendar
3. Check user's Google Account status

---

### Debugging Tips

1. **Enable Logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **Test with Google OAuth Playground**:
   - Visit [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)
   - Test token exchange manually

3. **Check Token Scopes**:
```python
token_info = google_oauth.token_info(access_token)
print(token_info['scope'])
```

4. **Verify Event Creation**:
   - Check user's Google Calendar directly
   - Use Google Calendar API Explorer

---

## Security Best Practices

1. **Encrypt Tokens**: Store OAuth tokens encrypted in database
2. **Use HTTPS**: All OAuth callbacks over HTTPS in production
3. **Validate State**: Always verify CSRF token in state parameter
4. **Minimal Scopes**: Only request `calendar.events` scope, not full calendar access
5. **Token Rotation**: Refresh tokens before expiration
6. **Revoke on Logout**: Offer users option to disconnect calendar

---

## Testing

### Manual Testing

1. Connect Google Calendar in user settings
2. Book an appointment
3. Verify event appears in Google Calendar
4. Reschedule appointment
5. Verify event updates in Google Calendar
6. Cancel appointment
7. Verify event is removed from Google Calendar

### Automated Testing

```python
def test_calendar_integration():
    # Mock Google API
    mock_service = MockGoogleCalendarService()
    
    # Create appointment
    appointment = create_appointment()
    
    # Assert event created
    assert mock_service.event_created(appointment.calendar_event_id)
    
    # Reschedule
    reschedule_appointment(appointment.id, new_time)
    
    # Assert event updated
    assert mock_service.event_updated(appointment.calendar_event_id)
```

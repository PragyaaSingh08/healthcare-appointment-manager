export type Role = 'PATIENT' | 'DOCTOR' | 'ADMIN'

export interface CurrentUser {
  id: string
  name: string
  email: string
  role: Role
  is_email_verified: boolean
}

export interface Doctor {
  id: string
  name: string
  specialization: string
  qualification: string | null
  experience: number | null
  slot_duration: number
  is_active: boolean
}

export interface SlotInterval {
  start: string
  end: string
}

export interface Hold {
  id: string
  doctor_id: string
  start_time: string
  end_time: string
  status: string
  expires_at: string
}

export type AppointmentStatus =
  | 'SCHEDULED'
  | 'RESCHEDULED'
  | 'CANCELLED'
  | 'COMPLETED'
  | 'RESCHEDULE_REQUIRED'

export interface Appointment {
  id: string
  patient_id: string
  doctor_id: string
  start_time: string
  end_time: string
  status: AppointmentStatus
  booking_reference: string
}

export interface PreVisitSummary {
  urgency: string | null
  chief_complaint: string | null
  suggested_questions: string[] | null
  status: 'PENDING' | 'SUCCESS' | 'FAILED'
}

export interface PostVisitSummary {
  summary: string | null
  medication_schedule: { medicine: string; dosage: string; frequency: string; instructions?: string }[] | null
  follow_up_steps: string[] | null
  status: 'PENDING' | 'SUCCESS' | 'FAILED'
}

export interface ApiError {
  error: { code: string; message: string }
}

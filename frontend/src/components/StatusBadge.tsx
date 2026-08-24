import type { AppointmentStatus } from '../types'

const STATUS_CLASS: Record<AppointmentStatus, string> = {
  SCHEDULED: 'badge-scheduled',
  RESCHEDULED: 'badge-scheduled',
  COMPLETED: 'badge-completed',
  CANCELLED: 'badge-cancelled',
  RESCHEDULE_REQUIRED: 'badge-medium',
}

const STATUS_LABEL: Record<AppointmentStatus, string> = {
  SCHEDULED: 'Scheduled',
  RESCHEDULED: 'Rescheduled',
  COMPLETED: 'Completed',
  CANCELLED: 'Cancelled',
  RESCHEDULE_REQUIRED: 'Needs rescheduling',
}

export function AppointmentStatusBadge({ status }: { status: AppointmentStatus }) {
  return <span className={`badge ${STATUS_CLASS[status]}`}>{STATUS_LABEL[status]}</span>
}

export function UrgencyBadge({ urgency }: { urgency: string }) {
  const cls = urgency === 'High' ? 'badge-urgent' : urgency === 'Medium' ? 'badge-medium' : 'badge-low'
  return <span className={`badge ${cls}`}>{urgency} urgency</span>
}

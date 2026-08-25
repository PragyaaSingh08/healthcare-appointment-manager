import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { appointmentsApi } from '../../services/api'
import type { Appointment } from '../../types'
import { AppointmentStatusBadge } from '../../components/StatusBadge'
import CalendarConnectButton from '../../components/CalendarConnectButton'
import { useAuth } from '../../context/AuthContext'

export default function PatientDashboard() {
  const { user } = useAuth()
  const [appointments, setAppointments] = useState<Appointment[] | null>(null)

  useEffect(() => {
    appointmentsApi.list().then((res) => setAppointments(res.data))
  }, [])

  const upcoming = appointments?.find((a) => a.status === 'SCHEDULED' || a.status === 'RESCHEDULED')

  return (
    <div className="p-8 max-w-4xl space-y-6">
      <div>
        <h1 className="font-display text-3xl text-forest-900 mb-1">Welcome back, {user?.name.split(' ')[0]}</h1>
        <p className="text-ink-400">Here's what's coming up.</p>
      </div>

      <CalendarConnectButton />

      <div className="card p-6">
        <h2 className="font-medium text-ink-700 mb-3">Next appointment</h2>
        {appointments === null && <p className="text-ink-400 text-sm">Loading…</p>}
        {appointments !== null && !upcoming && (
          <div className="text-center py-8">
            <p className="text-ink-400 mb-4">No upcoming appointments yet.</p>
            <Link to="/patient/doctors" className="btn-primary inline-block">
              Find a doctor
            </Link>
          </div>
        )}
        {upcoming && (
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-ink-900">
                {new Date(upcoming.start_time).toLocaleDateString(undefined, {
                  weekday: 'long',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
              <p className="text-ink-400 text-sm">
                {new Date(upcoming.start_time).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
              </p>
            </div>
            <AppointmentStatusBadge status={upcoming.status} />
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Link to="/patient/doctors" className="card p-6 hover:border-forest-600 transition-colors">
          <p className="font-medium text-ink-900 mb-1">Book an appointment</p>
          <p className="text-sm text-ink-400">Search doctors by specialization and see live availability.</p>
        </Link>
        <Link to="/patient/chat" className="card p-6 hover:border-forest-600 transition-colors">
          <p className="font-medium text-ink-900 mb-1">Ask the assistant</p>
          <p className="text-sm text-ink-400">Check appointments, medications, or find a doctor by chatting.</p>
        </Link>
      </div>
    </div>
  )
}

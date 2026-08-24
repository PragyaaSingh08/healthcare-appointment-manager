import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { appointmentsApi } from '../../services/api'
import type { Appointment } from '../../types'
import { AppointmentStatusBadge } from '../../components/StatusBadge'

export default function AppointmentList() {
  const [appointments, setAppointments] = useState<Appointment[] | null>(null)

  useEffect(() => {
    appointmentsApi.list().then(({ data }) => setAppointments(data))
  }, [])

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="font-display text-3xl text-forest-900 mb-1">My appointments</h1>
      <p className="text-ink-400 mb-6">Past and upcoming visits.</p>

      {appointments === null && <p className="text-ink-400 text-sm">Loading…</p>}
      {appointments !== null && appointments.length === 0 && (
        <div className="card p-8 text-center">
          <p className="text-ink-400 mb-4">You haven't booked any appointments yet.</p>
          <Link to="/patient/doctors" className="btn-primary inline-block">
            Find a doctor
          </Link>
        </div>
      )}
      <div className="space-y-3">
        {appointments?.map((a) => (
          <Link key={a.id} to={`/patient/appointments/${a.id}`} className="card p-5 flex items-center justify-between hover:border-forest-600 transition-colors">
            <div>
              <p className="font-medium text-ink-900">
                {new Date(a.start_time).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
                {' · '}
                {new Date(a.start_time).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
              </p>
              <p className="text-xs text-ink-400 font-mono mt-1">Ref: {a.booking_reference.slice(0, 8)}</p>
            </div>
            <AppointmentStatusBadge status={a.status} />
          </Link>
        ))}
      </div>
    </div>
  )
}

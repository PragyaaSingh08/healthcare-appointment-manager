import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { appointmentsApi } from '../../services/api'
import type { Appointment } from '../../types'
import { AppointmentStatusBadge } from '../../components/StatusBadge'
import CalendarConnectButton from '../../components/CalendarConnectButton'

export default function DoctorAppointmentList({ todayOnly = false }: { todayOnly?: boolean }) {
  const [appointments, setAppointments] = useState<Appointment[] | null>(null)

  useEffect(() => {
    appointmentsApi.list().then((res) => setAppointments(res.data))
  }, [])

  const filtered = todayOnly
    ? appointments?.filter((a) => new Date(a.start_time).toDateString() === new Date().toDateString())
    : appointments

  return (
    <div className="p-8 max-w-3xl space-y-6">
      <div>
        <h1 className="font-display text-3xl text-forest-900 mb-1">{todayOnly ? "Today's appointments" : 'All appointments'}</h1>
        <p className="text-ink-400">Review symptoms and AI summaries before each visit.</p>
      </div>

      <CalendarConnectButton />

      {filtered === undefined || filtered === null ? (
        <p className="text-ink-400 text-sm">Loading…</p>
      ) : filtered.length === 0 ? (
        <p className="text-ink-400 text-sm">No appointments to show.</p>
      ) : (
        <div className="space-y-3">
          {filtered.map((a) => (
            <Link key={a.id} to={`/doctor/appointments/${a.id}`} className="card p-5 flex items-center justify-between hover:border-forest-600 transition-colors">
              <div>
                <p className="font-medium text-ink-900">
                  {new Date(a.start_time).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
                  {' · '}
                  {new Date(a.start_time).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
                </p>
              </div>
              <AppointmentStatusBadge status={a.status} />
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

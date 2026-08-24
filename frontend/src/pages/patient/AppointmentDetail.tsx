import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { appointmentsApi, apiErrorMessage } from '../../services/api'
import type { Appointment, PostVisitSummary, PreVisitSummary } from '../../types'
import { AppointmentStatusBadge, UrgencyBadge } from '../../components/StatusBadge'
import { useToast } from '../../components/Toast'

export default function AppointmentDetail() {
  const { id } = useParams<{ id: string }>()
  const { show } = useToast()
  const [appointment, setAppointment] = useState<Appointment | null>(null)
  const [preVisit, setPreVisit] = useState<PreVisitSummary | null>(null)
  const [postVisit, setPostVisit] = useState<PostVisitSummary | null>(null)
  const [cancelling, setCancelling] = useState(false)

  useEffect(() => {
    if (!id) return
    appointmentsApi.get(id).then(({ data }) => setAppointment(data))
    appointmentsApi
      .preVisitSummary(id)
      .then(({ data }) => setPreVisit(data))
      .catch(() => setPreVisit(null))
    appointmentsApi
      .postVisitSummary(id)
      .then(({ data }) => setPostVisit(data))
      .catch(() => setPostVisit(null))
  }, [id])

  async function cancel() {
    if (!id || !appointment) return
    setCancelling(true)
    try {
      const { data } = await appointmentsApi.cancel(id)
      setAppointment(data)
      show('Appointment cancelled.')
    } catch (err) {
      show(apiErrorMessage(err), 'error')
    } finally {
      setCancelling(false)
    }
  }

  if (!appointment) return <div className="p-8 text-ink-400">Loading…</div>

  const canCancel = appointment.status === 'SCHEDULED' || appointment.status === 'RESCHEDULED'

  return (
    <div className="p-8 max-w-2xl space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-1">
          <h1 className="font-display text-3xl text-forest-900">Appointment</h1>
          <AppointmentStatusBadge status={appointment.status} />
        </div>
        <p className="text-ink-400 font-mono text-sm">Ref: {appointment.booking_reference}</p>
      </div>

      <div className="card p-6">
        <p className="font-medium text-ink-900">
          {new Date(appointment.start_time).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
        </p>
        <p className="text-ink-400 text-sm">
          {new Date(appointment.start_time).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })} –{' '}
          {new Date(appointment.end_time).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
        </p>
        {canCancel && (
          <div className="flex gap-3 mt-4">
            <Link to={`/patient/doctors/${appointment.doctor_id}?reschedule=${appointment.id}`} className="btn-secondary text-sm">
              Reschedule
            </Link>
            <button onClick={cancel} disabled={cancelling} className="btn-secondary text-sm">
              {cancelling ? 'Cancelling…' : 'Cancel appointment'}
            </button>
          </div>
        )}
      </div>

      <div className="card p-6">
        <h2 className="font-medium text-ink-700 mb-3">Pre-visit summary</h2>
        {!preVisit && <p className="text-sm text-ink-400">Not available.</p>}
        {preVisit?.status === 'FAILED' && (
          <p className="text-sm text-ink-400">AI summary is temporarily unavailable. Please review the information you submitted directly with your doctor.</p>
        )}
        {preVisit?.status === 'SUCCESS' && (
          <div className="space-y-3">
            {preVisit.urgency && <UrgencyBadge urgency={preVisit.urgency} />}
            <p className="text-sm text-ink-900">{preVisit.chief_complaint}</p>
            {preVisit.suggested_questions && (
              <div>
                <p className="text-xs font-medium text-ink-400 uppercase tracking-wide mb-1">Questions to ask your doctor</p>
                <ul className="text-sm text-ink-700 list-disc list-inside space-y-0.5">
                  {preVisit.suggested_questions.map((q, i) => (
                    <li key={i}>{q}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {postVisit?.status === 'SUCCESS' && (
        <div className="card p-6">
          <h2 className="font-medium text-ink-700 mb-3">Post-visit summary</h2>
          <p className="text-sm text-ink-900 mb-4">{postVisit.summary}</p>
          {postVisit.medication_schedule && postVisit.medication_schedule.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-medium text-ink-400 uppercase tracking-wide mb-2">Medication schedule</p>
              <div className="space-y-2">
                {postVisit.medication_schedule.map((m, i) => (
                  <div key={i} className="text-sm bg-sage-100 rounded-card px-3 py-2">
                    <span className="font-medium">{m.medicine}</span> — {m.dosage}, {m.frequency}
                    {m.instructions ? ` (${m.instructions})` : ''}
                  </div>
                ))}
              </div>
            </div>
          )}
          {postVisit.follow_up_steps && postVisit.follow_up_steps.length > 0 && (
            <div>
              <p className="text-xs font-medium text-ink-400 uppercase tracking-wide mb-1">Follow-up steps</p>
              <ul className="text-sm text-ink-700 list-disc list-inside space-y-0.5">
                {postVisit.follow_up_steps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

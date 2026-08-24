import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { appointmentsApi, doctorsApi, slotsApi } from '../../services/api'
import type { Doctor, SlotInterval } from '../../types'
import { apiErrorMessage } from '../../services/api'
import { useToast } from '../../components/Toast'

function todayISO(offsetDays = 0): string {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  return d.toISOString().split('T')[0]
}

type Step = 'browse' | 'symptoms' | 'confirming'

export default function DoctorProfile() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const rescheduleAppointmentId = searchParams.get('reschedule')
  const navigate = useNavigate()
  const { show } = useToast()

  const [doctor, setDoctor] = useState<Doctor | null>(null)
  const [date, setDate] = useState(todayISO(1))
  const [slots, setSlots] = useState<SlotInterval[]>([])
  const [loadingSlots, setLoadingSlots] = useState(true)
  const [step, setStep] = useState<Step>('browse')
  const [selectedSlot, setSelectedSlot] = useState<SlotInterval | null>(null)
  const [holdId, setHoldId] = useState<string | null>(null)
  const [holdExpiresAt, setHoldExpiresAt] = useState<Date | null>(null)
  const [symptoms, setSymptoms] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    doctorsApi.get(id).then(({ data }) => setDoctor(data))
  }, [id])

  useEffect(() => {
    if (!id) return
    setLoadingSlots(true)
    doctorsApi
      .availability(id, date)
      .then(({ data }) => setSlots(data.available_slots))
      .finally(() => setLoadingSlots(false))
  }, [id, date])

  async function selectSlot(slot: SlotInterval) {
    if (!id) return
    setError(null)
    try {
      const { data } = await slotsApi.hold(id, slot.start)
      setSelectedSlot(slot)
      setHoldId(data.id)
      setHoldExpiresAt(new Date(data.expires_at))
      if (rescheduleAppointmentId) {
        // No new symptoms needed for a reschedule — confirm immediately.
        await confirmReschedule(data.id)
      } else {
        setStep('symptoms')
      }
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  async function confirmReschedule(newHoldId: string) {
    if (!rescheduleAppointmentId) return
    setStep('confirming')
    setError(null)
    try {
      await appointmentsApi.reschedule(rescheduleAppointmentId, newHoldId)
      show('Appointment rescheduled.')
      navigate(`/patient/appointments/${rescheduleAppointmentId}`)
    } catch (err) {
      setError(apiErrorMessage(err))
      setStep('browse')
    }
  }

  async function confirmBooking() {
    if (!holdId) return
    setStep('confirming')
    setError(null)
    try {
      const { data } = await appointmentsApi.confirm(holdId, symptoms)
      show('Appointment confirmed.')
      navigate(`/patient/appointments/${data.id}`)
    } catch (err) {
      setError(apiErrorMessage(err))
      setStep('symptoms')
    }
  }

  function cancelHold() {
    if (holdId) slotsApi.release(holdId).catch(() => {})
    setStep('browse')
    setSelectedSlot(null)
    setHoldId(null)
  }

  if (!doctor) return <div className="p-8 text-ink-400">Loading…</div>

  return (
    <div className="p-8 max-w-3xl">
      <h1 className="font-display text-3xl text-forest-900 mb-1">{doctor.name}</h1>
      <p className="text-ink-400 mb-2">
        {doctor.specialization}
        {doctor.qualification ? ` · ${doctor.qualification}` : ''}
      </p>
      {rescheduleAppointmentId && (
        <p className="text-sm text-amber-600 bg-amber-100 rounded-card px-3 py-2 mb-6 inline-block">
          Choose a new slot to reschedule your existing appointment.
        </p>
      )}

      {step === 'confirming' && rescheduleAppointmentId && (
        <div className="card p-6 text-ink-400 text-sm">Rescheduling…</div>
      )}

      {step === 'browse' && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-medium text-ink-700">Available slots</h2>
            <input type="date" className="input w-auto" value={date} min={todayISO()} onChange={(e) => setDate(e.target.value)} />
          </div>
          {loadingSlots && <p className="text-ink-400 text-sm">Loading slots…</p>}
          {!loadingSlots && slots.length === 0 && (
            <p className="text-ink-400 text-sm">No slots available on this date. Try another day.</p>
          )}
          <div className="grid grid-cols-4 gap-2">
            {slots.map((s) => (
              <button
                key={s.start}
                onClick={() => selectSlot(s)}
                className="rounded-card border border-forest-100 px-3 py-2 text-sm font-medium hover:border-forest-600 hover:bg-forest-50 transition-colors"
              >
                {new Date(s.start).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
              </button>
            ))}
          </div>
          {error && <p className="text-clay-500 text-sm mt-4">{error}</p>}
        </div>
      )}

      {(step === 'symptoms' || step === 'confirming') && selectedSlot && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-medium text-ink-700">Tell us what's going on</h2>
            {holdExpiresAt && <HoldTimer expiresAt={holdExpiresAt} onExpire={cancelHold} />}
          </div>
          <p className="text-sm text-ink-400 mb-4">
            {new Date(selectedSlot.start).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
            {' · '}
            {new Date(selectedSlot.start).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
          </p>
          <textarea
            className="input h-32 mb-4"
            placeholder="Describe your symptoms — when they started, how severe, anything relevant."
            value={symptoms}
            onChange={(e) => setSymptoms(e.target.value)}
          />
          {error && <p className="text-clay-500 text-sm mb-4">{error}</p>}
          <div className="flex gap-3">
            <button onClick={cancelHold} className="btn-secondary" disabled={step === 'confirming'}>
              Cancel
            </button>
            <button onClick={confirmBooking} disabled={!symptoms.trim() || step === 'confirming'} className="btn-primary flex-1">
              {step === 'confirming' ? 'Confirming…' : 'Confirm appointment'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function HoldTimer({ expiresAt, onExpire }: { expiresAt: Date; onExpire: () => void }) {
  const [remaining, setRemaining] = useState(Math.max(0, expiresAt.getTime() - Date.now()))

  useEffect(() => {
    const interval = setInterval(() => {
      const left = expiresAt.getTime() - Date.now()
      setRemaining(Math.max(0, left))
      if (left <= 0) {
        clearInterval(interval)
        onExpire()
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [expiresAt, onExpire])

  const minutes = Math.floor(remaining / 60000)
  const seconds = Math.floor((remaining % 60000) / 1000)

  return (
    <span className="text-xs font-mono text-amber-600 bg-amber-100 rounded-full px-2.5 py-1">
      Slot held: {minutes}:{seconds.toString().padStart(2, '0')}
    </span>
  )
}

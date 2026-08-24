import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { appointmentsApi, apiErrorMessage } from '../../services/api'
import type { Appointment, PreVisitSummary } from '../../types'
import { UrgencyBadge } from '../../components/StatusBadge'
import { useToast } from '../../components/Toast'

interface RxItem {
  medicine_name: string
  dosage: string
  frequency: string
  duration: string
  instructions: string
}

const EMPTY_RX: RxItem = { medicine_name: '', dosage: '', frequency: 'ONCE_DAILY', duration: '', instructions: '' }

export default function ConsultationView() {
  const { id } = useParams<{ id: string }>()
  const { show } = useToast()
  const [appointment, setAppointment] = useState<Appointment | null>(null)
  const [preVisit, setPreVisit] = useState<PreVisitSummary | null>(null)
  const [history, setHistory] = useState<string | null>(null)
  const [notes, setNotes] = useState('')
  const [rxItems, setRxItems] = useState<RxItem[]>([{ ...EMPTY_RX }])
  const [savingNotes, setSavingNotes] = useState(false)
  const [savingRx, setSavingRx] = useState(false)

  useEffect(() => {
    if (!id) return
    appointmentsApi.get(id).then(({ data }) => setAppointment(data))
    appointmentsApi
      .preVisitSummary(id)
      .then(({ data }) => setPreVisit(data))
      .catch(() => setPreVisit(null))
    appointmentsApi
      .relevantHistory(id)
      .then(({ data }) => setHistory(data.context || null))
      .catch(() => setHistory(null))
    // Pre-fill with anything already saved, instead of always rendering a
    // blank form for a visit that already has notes/a prescription.
    appointmentsApi
      .getClinicalNotes(id)
      .then(({ data }) => {
        if (data.notes) setNotes(data.notes)
      })
      .catch(() => {})
    appointmentsApi
      .getPrescriptions(id)
      .then(({ data }) => {
        if (data.items.length > 0) {
          setRxItems(
            data.items.map((item) => ({
              medicine_name: item.medicine_name,
              dosage: item.dosage,
              frequency: item.frequency,
              duration: item.duration ?? '',
              instructions: item.instructions ?? '',
            })),
          )
        }
      })
      .catch(() => {})
  }, [id])

  async function saveNotes() {
    if (!id) return
    setSavingNotes(true)
    try {
      await appointmentsApi.addClinicalNotes(id, notes)
      show('Clinical notes saved.')
    } catch (err) {
      show(apiErrorMessage(err), 'error')
    } finally {
      setSavingNotes(false)
    }
  }

  async function savePrescription() {
    if (!id) return
    setSavingRx(true)
    try {
      await appointmentsApi.addPrescription(
        id,
        rxItems.filter((r) => r.medicine_name.trim()),
      )
      show('Prescription saved. Post-visit summary is generating.')
    } catch (err) {
      show(apiErrorMessage(err), 'error')
    } finally {
      setSavingRx(false)
    }
  }

  function updateRx(index: number, field: keyof RxItem, value: string) {
    setRxItems((prev) => prev.map((item, i) => (i === index ? { ...item, [field]: value } : item)))
  }

  if (!appointment) return <div className="p-8 text-ink-400">Loading…</div>

  const isCompleted = appointment.status === 'COMPLETED'

  return (
    <div className="p-8 max-w-2xl space-y-6">
      <div>
        <div className="flex items-center gap-3 mb-1">
          <h1 className="font-display text-3xl text-forest-900">Consultation</h1>
          {isCompleted && <span className="badge badge-completed">Completed</span>}
        </div>
        <p className="text-ink-400 text-sm">
          {new Date(appointment.start_time).toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' })}
          {' · '}
          {new Date(appointment.start_time).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}
        </p>
      </div>

      <div className="card p-6">
        <h2 className="font-medium text-ink-700 mb-3">Pre-visit AI summary</h2>
        {preVisit?.status === 'FAILED' && (
          <p className="text-sm text-ink-400">
            AI summary is temporarily unavailable. Please review the patient's submitted symptoms directly.
          </p>
        )}
        {preVisit?.status === 'SUCCESS' && (
          <div className="space-y-3">
            {preVisit.urgency && <UrgencyBadge urgency={preVisit.urgency} />}
            <p className="text-sm text-ink-900 font-medium">{preVisit.chief_complaint}</p>
            {preVisit.suggested_questions && (
              <ul className="text-sm text-ink-700 list-disc list-inside space-y-0.5">
                {preVisit.suggested_questions.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ul>
            )}
            <p className="text-xs text-ink-400 pt-2 border-t border-forest-100">
              Decision-support only — not a diagnosis. Confirm directly with the patient.
            </p>
          </div>
        )}
      </div>

      {history && (
        <div className="card p-6">
          <h2 className="font-medium text-ink-700 mb-3">Relevant patient history</h2>
          <p className="text-xs text-ink-400 mb-3">
            Retrieved from this patient's own prior visits only — never another patient's records.
          </p>
          <p className="text-sm text-ink-900 whitespace-pre-line">{history}</p>
        </div>
      )}

      <div className="card p-6">
        <h2 className="font-medium text-ink-700 mb-3">Clinical notes</h2>
        <textarea className="input h-32 mb-3" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Consultation notes…" />
        <button onClick={saveNotes} disabled={!notes.trim() || savingNotes} className="btn-secondary text-sm">
          {savingNotes ? 'Saving…' : 'Save notes'}
        </button>
      </div>

      <div className="card p-6">
        <h2 className="font-medium text-ink-700 mb-3">Prescription</h2>
        {isCompleted ? (
          <div className="space-y-2">
            <p className="text-xs text-ink-400 mb-2">This visit is complete — medications prescribed:</p>
            {rxItems
              .filter((r) => r.medicine_name.trim())
              .map((item, i) => (
                <div key={i} className="text-sm bg-sage-100 rounded-card px-3 py-2">
                  <span className="font-medium">{item.medicine_name}</span> — {item.dosage}, {item.frequency}
                  {item.duration ? `, ${item.duration}` : ''}
                  {item.instructions ? ` (${item.instructions})` : ''}
                </div>
              ))}
          </div>
        ) : (
          <>
            <div className="space-y-3 mb-3">
              {rxItems.map((item, i) => (
                <div key={i} className="grid grid-cols-2 gap-2">
                  <input className="input" placeholder="Medicine" value={item.medicine_name} onChange={(e) => updateRx(i, 'medicine_name', e.target.value)} />
                  <input className="input" placeholder="Dosage (e.g. 500mg)" value={item.dosage} onChange={(e) => updateRx(i, 'dosage', e.target.value)} />
                  <select className="input" value={item.frequency} onChange={(e) => updateRx(i, 'frequency', e.target.value)}>
                    <option value="ONCE_DAILY">Once daily</option>
                    <option value="TWICE_DAILY">Twice daily</option>
                    <option value="THREE_TIMES_DAILY">Three times daily</option>
                    <option value="FOUR_TIMES_DAILY">Four times daily</option>
                  </select>
                  <input className="input" placeholder="Duration (e.g. 7 days)" value={item.duration} onChange={(e) => updateRx(i, 'duration', e.target.value)} />
                  <input className="input col-span-2" placeholder="Instructions (optional)" value={item.instructions} onChange={(e) => updateRx(i, 'instructions', e.target.value)} />
                </div>
              ))}
            </div>
            <div className="flex gap-3">
              <button onClick={() => setRxItems((prev) => [...prev, { ...EMPTY_RX }])} className="btn-secondary text-sm">
                + Add medication
              </button>
              <button onClick={savePrescription} disabled={savingRx} className="btn-primary text-sm">
                {savingRx ? 'Saving…' : 'Save & complete visit'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

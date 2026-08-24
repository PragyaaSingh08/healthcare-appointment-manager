import { useEffect, useState, type FormEvent } from 'react'
import api, { apiErrorMessage } from '../../services/api'
import type { Doctor } from '../../types'
import { useToast } from '../../components/Toast'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function AdminDoctors() {
  const { show } = useToast()
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [showForm, setShowForm] = useState(false)

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [specialization, setSpecialization] = useState('')
  const [qualification, setQualification] = useState('')
  const [experience, setExperience] = useState('')
  const [slotDuration, setSlotDuration] = useState('30')
  const [activeDays, setActiveDays] = useState<number[]>([0, 1, 2, 3, 4])
  const [submitting, setSubmitting] = useState(false)

  function loadDoctors() {
    api.get<Doctor[]>('/doctors').then(({ data }) => setDoctors(data))
  }

  useEffect(loadDoctors, [])

  function toggleDay(day: number) {
    setActiveDays((prev) => (prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.post('/doctors', {
        name,
        email,
        password,
        specialization,
        qualification: qualification || null,
        experience: experience ? Number(experience) : null,
        slot_duration: Number(slotDuration),
        working_hours: activeDays.map((d) => ({ day_of_week: d, start_time: '09:00:00', end_time: '17:00:00' })),
      })
      show('Doctor added.')
      setShowForm(false)
      setName('')
      setEmail('')
      setPassword('')
      setSpecialization('')
      setQualification('')
      setExperience('')
      loadDoctors()
    } catch (err) {
      show(apiErrorMessage(err), 'error')
    } finally {
      setSubmitting(false)
    }
  }

  async function addLeave(doctorId: string) {
    const date = window.prompt('Leave date (YYYY-MM-DD)?')
    if (!date) return
    try {
      const { data } = await api.post(`/doctors/${doctorId}/leave`, { leave_date: date, reason: 'Unavailable' })
      show(`Leave added. ${data.affected_appointments} affected patient(s) notified.`)
    } catch (err) {
      show(apiErrorMessage(err), 'error')
    }
  }

  return (
    <div className="p-8 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-3xl text-forest-900 mb-1">Doctors</h1>
          <p className="text-ink-400">Manage specialization, hours, and leave.</p>
        </div>
        <button onClick={() => setShowForm((v) => !v)} className="btn-primary">
          {showForm ? 'Cancel' : '+ Add doctor'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={onSubmit} className="card p-6 mb-6 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input className="input" placeholder="Full name" required value={name} onChange={(e) => setName(e.target.value)} />
            <input className="input" type="email" placeholder="Email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            <input className="input" type="password" placeholder="Temporary password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
            <input className="input" placeholder="Specialization" required value={specialization} onChange={(e) => setSpecialization(e.target.value)} />
            <input className="input" placeholder="Qualification" value={qualification} onChange={(e) => setQualification(e.target.value)} />
            <input className="input" type="number" placeholder="Years of experience" value={experience} onChange={(e) => setExperience(e.target.value)} />
            <input className="input" type="number" placeholder="Slot duration (minutes)" value={slotDuration} onChange={(e) => setSlotDuration(e.target.value)} />
          </div>
          <div>
            <p className="text-sm font-medium text-ink-700 mb-2">Working days (9am–5pm)</p>
            <div className="flex gap-2">
              {WEEKDAYS.map((label, i) => (
                <button
                  type="button"
                  key={label}
                  onClick={() => toggleDay(i)}
                  className={`rounded-full px-3 py-1 text-sm border ${
                    activeDays.includes(i) ? 'bg-forest-700 text-white border-forest-700' : 'border-forest-100 text-ink-700'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <button type="submit" disabled={submitting} className="btn-primary">
            {submitting ? 'Adding…' : 'Add doctor'}
          </button>
        </form>
      )}

      <div className="space-y-3">
        {doctors.map((d) => (
          <div key={d.id} className="card p-5 flex items-center justify-between">
            <div>
              <p className="font-medium text-ink-900">{d.name}</p>
              <p className="text-sm text-ink-400">{d.specialization}</p>
            </div>
            <button onClick={() => addLeave(d.id)} className="btn-secondary text-sm">
              Add leave
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

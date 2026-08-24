import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { doctorsApi } from '../../services/api'
import type { Doctor } from '../../types'

const SPECIALIZATIONS = ['', 'General Medicine', 'Cardiology', 'Dermatology', 'Pediatrics', 'Orthopedics']

export default function DoctorSearch() {
  const [specialization, setSpecialization] = useState('')
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const timeout = setTimeout(() => {
      doctorsApi
        .list(specialization || undefined)
        .then(({ data }) => setDoctors(data))
        .finally(() => setLoading(false))
    }, 250) // debounced search
    return () => clearTimeout(timeout)
  }, [specialization])

  return (
    <div className="p-8 max-w-4xl">
      <h1 className="font-display text-3xl text-forest-900 mb-1">Find a doctor</h1>
      <p className="text-ink-400 mb-6">Search by specialization and view available slots.</p>

      <select className="input mb-6 max-w-xs" value={specialization} onChange={(e) => setSpecialization(e.target.value)}>
        {SPECIALIZATIONS.map((s) => (
          <option key={s} value={s}>
            {s || 'All specializations'}
          </option>
        ))}
      </select>

      {loading && <p className="text-ink-400 text-sm">Loading doctors…</p>}
      {!loading && doctors.length === 0 && <p className="text-ink-400 text-sm">No doctors found for this filter.</p>}

      <div className="space-y-3">
        {doctors.map((d) => (
          <Link key={d.id} to={`/patient/doctors/${d.id}`} className="card p-5 flex items-center justify-between hover:border-forest-600 transition-colors">
            <div>
              <p className="font-medium text-ink-900">{d.name}</p>
              <p className="text-sm text-ink-400">
                {d.specialization}
                {d.qualification ? ` · ${d.qualification}` : ''}
                {d.experience ? ` · ${d.experience} yrs experience` : ''}
              </p>
            </div>
            <span className="text-forest-700 text-sm font-medium">View availability →</span>
          </Link>
        ))}
      </div>
    </div>
  )
}

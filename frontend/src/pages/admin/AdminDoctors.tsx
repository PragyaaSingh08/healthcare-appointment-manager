import { useEffect, useState, type FormEvent } from 'react'
import api, { doctorsApi, apiErrorMessage } from '../../services/api'
import type { Doctor, DoctorLeave } from '../../types'
import { useToast } from '../../components/Toast'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function AdminDoctors() {
  const { show } = useToast()
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'active' | 'deactivated'>('all')

  // Create form state
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createEmail, setCreateEmail] = useState('')
  const [createPassword, setCreatePassword] = useState('')
  const [createSpecialization, setCreateSpecialization] = useState('')
  const [createQualification, setCreateQualification] = useState('')
  const [createExperience, setCreateExperience] = useState('')
  const [createSlotDuration, setCreateSlotDuration] = useState('30')
  const [activeDays, setActiveDays] = useState<number[]>([0, 1, 2, 3, 4])
  const [submittingCreate, setSubmittingCreate] = useState(false)

  // Edit modal state
  const [editingDoctor, setEditingDoctor] = useState<Doctor | null>(null)
  const [editSpecialization, setEditSpecialization] = useState('')
  const [editQualification, setEditQualification] = useState('')
  const [editExperience, setEditExperience] = useState('')
  const [editSlotDuration, setEditSlotDuration] = useState('30')
  const [editIsActive, setEditIsActive] = useState(true)
  const [savingEdit, setSavingEdit] = useState(false)

  // Deactivate modal state
  const [deactivatingDoctor, setDeactivatingDoctor] = useState<Doctor | null>(null)
  const [togglingStatus, setTogglingStatus] = useState(false)

  // Leave modal state
  const [leaveDoctor, setLeaveDoctor] = useState<Doctor | null>(null)
  const [doctorLeaves, setDoctorLeaves] = useState<DoctorLeave[]>([])
  const [loadingLeaves, setLoadingLeaves] = useState(false)
  const [newLeaveDate, setNewLeaveDate] = useState('')
  const [newLeaveReason, setNewLeaveReason] = useState('')
  const [addingLeave, setAddingLeave] = useState(false)
  const [deletingLeaveId, setDeletingLeaveId] = useState<string | null>(null)

  function loadDoctors() {
    setLoading(true)
    doctorsApi
      .list()
      .then((res) => setDoctors(res.data))
      .catch((err) => show(apiErrorMessage(err), 'error'))
      .finally(() => setLoading(false))
  }

  useEffect(loadDoctors, [])

  function toggleDay(day: number) {
    setActiveDays((prev) => (prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]))
  }

  // Create Doctor
  async function onCreateSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmittingCreate(true)
    try {
      await api.post('/doctors', {
        name: createName,
        email: createEmail,
        password: createPassword,
        specialization: createSpecialization,
        qualification: createQualification || null,
        experience: createExperience ? Number(createExperience) : null,
        slot_duration: Number(createSlotDuration),
        working_hours: activeDays.map((d) => ({ day_of_week: d, start_time: '09:00:00', end_time: '17:00:00' })),
      })
      show('Doctor added successfully.')
      setShowCreateForm(false)
      setCreateName('')
      setCreateEmail('')
      setCreatePassword('')
      setCreateSpecialization('')
      setCreateQualification('')
      setCreateExperience('')
      loadDoctors()
    } catch (err) {
      show(apiErrorMessage(err), 'error')
    } finally {
      setSubmittingCreate(false)
    }
  }

  // Edit Doctor
  function openEditModal(doctor: Doctor) {
    setEditingDoctor(doctor)
    setEditSpecialization(doctor.specialization)
    setEditQualification(doctor.qualification || '')
    setEditExperience(doctor.experience ? String(doctor.experience) : '')
    setEditSlotDuration(String(doctor.slot_duration))
    setEditIsActive(doctor.is_active)
  }

  async function onEditSubmit(e: FormEvent) {
    e.preventDefault()
    if (!editingDoctor) return
    setSavingEdit(true)
    try {
      await doctorsApi.update(editingDoctor.id, {
        specialization: editSpecialization,
        qualification: editQualification || null,
        experience: editExperience ? Number(editExperience) : null,
        slot_duration: Number(editSlotDuration),
        is_active: editIsActive,
      })
      show('Doctor profile updated successfully.')
      setEditingDoctor(null)
      loadDoctors()
    } catch (err) {
      show(apiErrorMessage(err), 'error')
    } finally {
      setSavingEdit(false)
    }
  }

  // Deactivate / Reactivate
  function promptToggleStatus(doctor: Doctor) {
    setDeactivatingDoctor(doctor)
  }

  async function confirmToggleStatus() {
    if (!deactivatingDoctor) return
    setTogglingStatus(true)
    try {
      if (deactivatingDoctor.is_active) {
        await doctorsApi.deactivate(deactivatingDoctor.id)
        show(`Dr. ${deactivatingDoctor.name} has been deactivated.`)
      } else {
        await doctorsApi.update(deactivatingDoctor.id, { is_active: true })
        show(`Dr. ${deactivatingDoctor.name} has been reactivated.`)
      }
      setDeactivatingDoctor(null)
      loadDoctors()
    } catch (err) {
      show(apiErrorMessage(err), 'error')
    } finally {
      setTogglingStatus(false)
    }
  }

  // Manage Leaves
  async function openLeaveModal(doctor: Doctor) {
    setLeaveDoctor(doctor)
    setNewLeaveDate('')
    setNewLeaveReason('')
    setDoctorLeaves([])
    setLoadingLeaves(true)
    try {
      const res = await doctorsApi.getLeaves(doctor.id)
      setDoctorLeaves(res.data)
    } catch (err) {
      show(apiErrorMessage(err), 'error')
    } finally {
      setLoadingLeaves(false)
    }
  }

  async function onAddLeaveSubmit(e: FormEvent) {
    e.preventDefault()
    if (!leaveDoctor || !newLeaveDate) return
    setAddingLeave(true)
    try {
      const res = await doctorsApi.addLeave(leaveDoctor.id, newLeaveDate, newLeaveReason || undefined)
      const affected = res.data.affected_appointments
      show(
        `Leave scheduled for ${newLeaveDate}.${
          affected > 0 ? ` ${affected} appointment(s) updated to Reschedule Required.` : ''
        }`,
      )
      setNewLeaveDate('')
      setNewLeaveReason('')
      // Refresh leaves list
      const updated = await doctorsApi.getLeaves(leaveDoctor.id)
      setDoctorLeaves(updated.data)
    } catch (err) {
      show(apiErrorMessage(err), 'error')
    } finally {
      setAddingLeave(false)
    }
  }

  async function onDeleteLeave(leaveId: string) {
    if (!leaveDoctor) return
    setDeletingLeaveId(leaveId)
    try {
      await doctorsApi.deleteLeave(leaveDoctor.id, leaveId)
      show('Leave record removed.')
      setDoctorLeaves((prev) => prev.filter((l) => l.id !== leaveId))
    } catch (err) {
      show(apiErrorMessage(err), 'error')
    } finally {
      setDeletingLeaveId(null)
    }
  }

  const filteredDoctors = doctors.filter((d) => {
    if (filter === 'active') return d.is_active
    if (filter === 'deactivated') return !d.is_active
    return true
  })

  return (
    <div className="p-8 max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl text-forest-900 mb-1">Doctor Management</h1>
          <p className="text-ink-400">Manage profiles, slot durations, availability, and leaves.</p>
        </div>
        <button onClick={() => setShowCreateForm((v) => !v)} className="btn-primary">
          {showCreateForm ? 'Cancel' : '+ Add doctor'}
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-forest-100 pb-2">
        <button
          onClick={() => setFilter('all')}
          className={`text-sm px-3 py-1.5 rounded-card font-medium transition-colors ${
            filter === 'all' ? 'bg-forest-700 text-white' : 'text-ink-400 hover:text-ink-700'
          }`}
        >
          All Doctors ({doctors.length})
        </button>
        <button
          onClick={() => setFilter('active')}
          className={`text-sm px-3 py-1.5 rounded-card font-medium transition-colors ${
            filter === 'active' ? 'bg-forest-700 text-white' : 'text-ink-400 hover:text-ink-700'
          }`}
        >
          Active ({doctors.filter((d) => d.is_active).length})
        </button>
        <button
          onClick={() => setFilter('deactivated')}
          className={`text-sm px-3 py-1.5 rounded-card font-medium transition-colors ${
            filter === 'deactivated' ? 'bg-forest-700 text-white' : 'text-ink-400 hover:text-ink-700'
          }`}
        >
          Deactivated ({doctors.filter((d) => !d.is_active).length})
        </button>
      </div>

      {/* Create Doctor Form */}
      {showCreateForm && (
        <form onSubmit={onCreateSubmit} className="card p-6 space-y-4 border border-forest-200">
          <h2 className="font-display text-xl text-forest-900">Add New Doctor</h2>
          <div className="grid grid-cols-2 gap-3">
            <input
              className="input"
              placeholder="Full name"
              required
              value={createName}
              onChange={(e) => setCreateName(e.target.value)}
            />
            <input
              className="input"
              type="email"
              placeholder="Email address"
              required
              value={createEmail}
              onChange={(e) => setCreateEmail(e.target.value)}
            />
            <input
              className="input"
              type="password"
              placeholder="Temporary password (min 8 chars)"
              required
              minLength={8}
              value={createPassword}
              onChange={(e) => setCreatePassword(e.target.value)}
            />
            <input
              className="input"
              placeholder="Specialization (e.g. Cardiology)"
              required
              value={createSpecialization}
              onChange={(e) => setCreateSpecialization(e.target.value)}
            />
            <input
              className="input"
              placeholder="Qualification (e.g. MBBS, MD)"
              value={createQualification}
              onChange={(e) => setCreateQualification(e.target.value)}
            />
            <input
              className="input"
              type="number"
              placeholder="Years of experience"
              value={createExperience}
              onChange={(e) => setCreateExperience(e.target.value)}
            />
            <div className="col-span-2">
              <label className="text-xs text-ink-400 block mb-1">Appointment Slot Duration (Minutes)</label>
              <input
                className="input"
                type="number"
                min="10"
                max="120"
                step="5"
                placeholder="Slot duration (e.g. 30)"
                value={createSlotDuration}
                onChange={(e) => setCreateSlotDuration(e.target.value)}
              />
            </div>
          </div>
          <div>
            <p className="text-sm font-medium text-ink-700 mb-2">Weekly Working Days (9:00 AM – 5:00 PM)</p>
            <div className="flex gap-2">
              {WEEKDAYS.map((label, i) => (
                <button
                  type="button"
                  key={label}
                  onClick={() => toggleDay(i)}
                  className={`rounded-full px-3.5 py-1 text-sm font-medium border transition-colors ${
                    activeDays.includes(i) ? 'bg-forest-700 text-white border-forest-700' : 'border-forest-100 text-ink-700 hover:bg-forest-50'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={() => setShowCreateForm(false)} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={submittingCreate} className="btn-primary flex-1">
              {submittingCreate ? 'Adding Doctor…' : 'Save Doctor Profile'}
            </button>
          </div>
        </form>
      )}

      {/* Doctor Cards */}
      {loading ? (
        <p className="text-ink-400 text-sm py-4">Loading doctors…</p>
      ) : filteredDoctors.length === 0 ? (
        <p className="text-ink-400 text-sm py-8 text-center card p-6">No doctors found in this category.</p>
      ) : (
        <div className="space-y-3">
          {filteredDoctors.map((d) => (
            <div
              key={d.id}
              className={`card p-5 flex items-center justify-between transition-colors ${
                !d.is_active ? 'bg-gray-50 border-gray-200 opacity-80' : ''
              }`}
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-ink-900 text-base">{d.name}</p>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      d.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-200 text-gray-700'
                    }`}
                  >
                    {d.is_active ? 'Active' : 'Deactivated'}
                  </span>
                </div>
                <p className="text-sm text-ink-400">
                  <span className="text-forest-800 font-medium">{d.specialization}</span>
                  {d.qualification ? ` · ${d.qualification}` : ''}
                  {d.experience ? ` · ${d.experience} yrs exp` : ''}
                  {` · ${d.slot_duration} min slots`}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button onClick={() => openEditModal(d)} className="btn-secondary text-xs px-3 py-1.5">
                  Edit
                </button>
                <button onClick={() => openLeaveModal(d)} className="btn-secondary text-xs px-3 py-1.5">
                  Leaves
                </button>
                <button
                  onClick={() => setDeactivatingDoctor(d)}
                  className={`text-xs px-3 py-1.5 rounded-card border transition-colors ${
                    d.is_active
                      ? 'border-clay-200 text-clay-500 hover:bg-clay-50'
                      : 'border-emerald-200 text-emerald-700 hover:bg-emerald-50'
                  }`}
                >
                  {d.is_active ? 'Deactivate' : 'Reactivate'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Edit Doctor Modal */}
      {editingDoctor && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="card p-6 max-w-lg w-full space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-forest-100 pb-3">
              <h2 className="font-display text-xl text-forest-900">Edit Dr. {editingDoctor.name}</h2>
              <button onClick={() => setEditingDoctor(null)} className="text-ink-400 hover:text-ink-700 text-lg">
                ✕
              </button>
            </div>
            <form onSubmit={onEditSubmit} className="space-y-3">
              <div>
                <label className="text-xs text-ink-400 block mb-1">Specialization</label>
                <input
                  className="input"
                  required
                  value={editSpecialization}
                  onChange={(e) => setEditSpecialization(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-ink-400 block mb-1">Qualification</label>
                  <input
                    className="input"
                    value={editQualification}
                    onChange={(e) => setEditQualification(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs text-ink-400 block mb-1">Experience (Years)</label>
                  <input
                    className="input"
                    type="number"
                    value={editExperience}
                    onChange={(e) => setEditExperience(e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-ink-400 block mb-1">Slot Duration (Minutes)</label>
                <input
                  className="input"
                  type="number"
                  min="10"
                  max="120"
                  step="5"
                  required
                  value={editSlotDuration}
                  onChange={(e) => setEditSlotDuration(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="editIsActive"
                  checked={editIsActive}
                  onChange={(e) => setEditIsActive(e.target.checked)}
                  className="rounded border-forest-300 text-forest-700 focus:ring-forest-500 w-4 h-4"
                />
                <label htmlFor="editIsActive" className="text-sm font-medium text-ink-700 cursor-pointer">
                  Doctor profile is active and open for bookings
                </label>
              </div>
              <div className="flex gap-3 pt-3">
                <button type="button" onClick={() => setEditingDoctor(null)} className="btn-secondary flex-1">
                  Cancel
                </button>
                <button type="submit" disabled={savingEdit} className="btn-primary flex-1">
                  {savingEdit ? 'Saving…' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Deactivate / Reactivate Confirmation Modal */}
      {deactivatingDoctor && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="card p-6 max-w-md w-full space-y-4 shadow-xl">
            <h2 className="font-display text-xl text-forest-900">
              {deactivatingDoctor.is_active ? 'Deactivate Doctor' : 'Reactivate Doctor'}
            </h2>
            <p className="text-sm text-ink-700">
              {deactivatingDoctor.is_active
                ? `Are you sure you want to deactivate Dr. ${deactivatingDoctor.name}? They will no longer appear in patient searches for new appointments.`
                : `Are you sure you want to reactivate Dr. ${deactivatingDoctor.name}? Their profile will become visible for patient bookings again.`}
            </p>
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setDeactivatingDoctor(null)}
                className="btn-secondary flex-1"
                disabled={togglingStatus}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmToggleStatus}
                disabled={togglingStatus}
                className={`flex-1 font-medium text-sm rounded-card px-4 py-2 text-white transition-colors ${
                  deactivatingDoctor.is_active
                    ? 'bg-clay-500 hover:bg-clay-600'
                    : 'bg-forest-700 hover:bg-forest-800'
                }`}
              >
                {togglingStatus ? 'Updating…' : deactivatingDoctor.is_active ? 'Yes, Deactivate' : 'Yes, Reactivate'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Leave Management Modal */}
      {leaveDoctor && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="card p-6 max-w-lg w-full space-y-5 shadow-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-forest-100 pb-3">
              <div>
                <h2 className="font-display text-xl text-forest-900">Manage Leaves</h2>
                <p className="text-xs text-ink-400">Dr. {leaveDoctor.name} ({leaveDoctor.specialization})</p>
              </div>
              <button onClick={() => setLeaveDoctor(null)} className="text-ink-400 hover:text-ink-700 text-lg">
                ✕
              </button>
            </div>

            {/* Schedule New Leave Form */}
            <form onSubmit={onAddLeaveSubmit} className="bg-forest-50/60 rounded-card p-4 space-y-3 border border-forest-100">
              <p className="text-sm font-medium text-forest-900">Schedule New Leave Date</p>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-ink-400 block mb-1">Leave Date</label>
                  <input
                    type="date"
                    required
                    min={new Date().toISOString().split('T')[0]}
                    value={newLeaveDate}
                    onChange={(e) => setNewLeaveDate(e.target.value)}
                    className="input text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-ink-400 block mb-1">Reason (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. Vacation, Conference"
                    value={newLeaveReason}
                    onChange={(e) => setNewLeaveReason(e.target.value)}
                    className="input text-sm"
                  />
                </div>
              </div>
              <p className="text-xs text-amber-700 bg-amber-50 rounded p-2 border border-amber-200">
                Any existing patient appointments on this date will be automatically transitioned to <strong>Reschedule Required</strong> and affected patients will receive conflict notification emails.
              </p>
              <button
                type="submit"
                disabled={addingLeave || !newLeaveDate}
                className="btn-primary text-xs w-full py-2"
              >
                {addingLeave ? 'Scheduling Leave…' : '+ Schedule Doctor Leave'}
              </button>
            </form>

            {/* Existing Leaves List */}
            <div className="space-y-3">
              <p className="text-sm font-medium text-ink-700">Scheduled Leaves</p>
              {loadingLeaves ? (
                <p className="text-xs text-ink-400">Loading leave records…</p>
              ) : doctorLeaves.length === 0 ? (
                <p className="text-xs text-ink-400 italic py-2">No upcoming leaves scheduled for this doctor.</p>
              ) : (
                <div className="space-y-2">
                  {doctorLeaves.map((l) => (
                    <div
                      key={l.id}
                      className="flex items-center justify-between text-sm bg-canvas border border-forest-100 rounded-card px-3.5 py-2.5"
                    >
                      <div>
                        <p className="font-medium text-ink-900">
                          {new Date(l.leave_date + 'T00:00:00Z').toLocaleDateString(undefined, {
                            weekday: 'short',
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            timeZone: 'UTC',
                          })}
                        </p>
                        {l.reason && <p className="text-xs text-ink-400">{l.reason}</p>}
                      </div>
                      <button
                        type="button"
                        onClick={() => onDeleteLeave(l.id)}
                        disabled={deletingLeaveId === l.id}
                        className="text-xs text-clay-500 hover:text-clay-600 underline font-medium px-2 py-1"
                      >
                        {deletingLeaveId === l.id ? 'Deleting…' : 'Delete Leave'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="pt-2 border-t border-forest-100">
              <button type="button" onClick={() => setLeaveDoctor(null)} className="btn-secondary text-sm w-full">
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

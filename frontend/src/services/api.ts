import axios from 'axios'
import type {
  Appointment,
  CalendarStatus,
  CurrentUser,
  Doctor,
  DoctorLeave,
  Hold,
  PostVisitSummary,
  PreVisitSummary,
  SlotInterval,
} from '../types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
})
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Centralized error shape unwrapping so components can just read `.message`.
export function apiErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { error?: { message?: string }; detail?: string } | undefined
    if (data?.error?.message) return data.error.message
    if (typeof data?.detail === 'string') return data.detail
  }
  if (err instanceof Error && err.message) {
    return err.message
  }
  return 'Something went wrong. Please try again.'
}

export const authApi = {
  register: (name: string, email: string, password: string) =>
    api.post<{ access_token: string; role: string }>('/auth/register', { name, email, password }),
  login: (email: string, password: string) =>
    api.post<{ access_token: string; role: string }>('/auth/login', { email, password }),
  me: () => api.get<CurrentUser>('/auth/me'),
  forgotPassword: (email: string) => api.post<{ message: string }>('/auth/forgot-password', { email }),
  resetPassword: (token: string, newPassword: string) =>
    api.post<{ message: string }>('/auth/reset-password', { token, new_password: newPassword }),
  verifyEmail: (token: string) => api.post<{ message: string }>('/auth/verify-email', { token }),
  resendVerification: () => api.post<{ message: string }>('/auth/resend-verification'),
}

export const doctorsApi = {
  list: (specialization?: string, isActive?: boolean) =>
    api.get<Doctor[]>('/doctors', {
      params: {
        ...(specialization ? { specialization } : {}),
        ...(isActive !== undefined ? { is_active: isActive } : {}),
      },
    }),
  get: (id: string) => api.get<Doctor>(`/doctors/${id}`),
  update: (
    id: string,
    payload: {
      specialization?: string
      qualification?: string | null
      experience?: number | null
      slot_duration?: number
      is_active?: boolean
    },
  ) => api.put<Doctor>(`/doctors/${id}`, payload),
  deactivate: (id: string) => api.delete(`/doctors/${id}`),
  availability: (id: string, date: string) =>
    api.get<{ date: string; available_slots: SlotInterval[] }>(`/doctors/${id}/availability`, { params: { date } }),
  getLeaves: (doctorId: string) =>
    api.get<DoctorLeave[]>(`/doctors/${doctorId}/leave`),
  addLeave: (doctorId: string, leaveDate: string, reason?: string) =>
    api.post<{ id: string; leave_date: string; affected_appointments: number }>(`/doctors/${doctorId}/leave`, {
      leave_date: leaveDate,
      reason,
    }),
  deleteLeave: (doctorId: string, leaveId: string) =>
    api.delete(`/doctors/${doctorId}/leave/${leaveId}`),
}

export const calendarApi = {
  connect: () => api.post<{ auth_url: string }>('/calendar/connect'),
  callback: (code: string, state: string) =>
    api.get<{ status: string }>('/calendar/callback', { params: { code, state } }),
  status: () => api.get<CalendarStatus>('/calendar/status'),
}

export const slotsApi = {
  hold: (doctorId: string, startTime: string) =>
    api.post<Hold>('/slots/hold', { doctor_id: doctorId, start_time: startTime }),
  release: (holdId: string) => api.delete(`/slots/${holdId}`),
}

export const appointmentsApi = {
  confirm: (holdId: string, symptoms: string) =>
    api.post<Appointment>(`/appointments/confirm/${holdId}`, { symptoms }),
  list: () => api.get<Appointment[]>('/appointments'),
  get: (id: string) => api.get<Appointment>(`/appointments/${id}`),
  cancel: (id: string) => api.post<Appointment>(`/appointments/${id}/cancel`),
  reschedule: (id: string, holdId: string) =>
    api.put<Appointment>(`/appointments/${id}/reschedule`, { hold_id: holdId }),
  preVisitSummary: (id: string) => api.get<PreVisitSummary>(`/appointments/${id}/previsit-summary`),
  relevantHistory: (id: string) => api.get<{ context: string }>(`/appointments/${id}/relevant-history`),
  postVisitSummary: (id: string) => api.get<PostVisitSummary>(`/appointments/${id}/postvisit-summary`),
  addClinicalNotes: (id: string, notes: string) => api.post(`/appointments/${id}/clinical-notes`, { notes }),
  getClinicalNotes: (id: string) => api.get<{ notes: string | null }>(`/appointments/${id}/clinical-notes`),
  addPrescription: (
    id: string,
    items: { medicine_name: string; dosage: string; frequency: string; duration?: string; instructions?: string }[],
  ) => api.post(`/appointments/${id}/prescription`, { items }),
  getPrescriptions: (id: string) =>
    api.get<{
      items: { medicine_name: string; dosage: string; frequency: string; duration: string | null; instructions: string | null }[]
    }>(`/appointments/${id}/prescriptions`),
}

export const chatApi = {
  createSession: () => api.post<{ id: string; status: string }>('/chat/sessions'),
  sendMessage: (sessionId: string, message: string) =>
    api.post<{ session_id: string; reply: string }>(`/chat/sessions/${sessionId}/messages`, { message }),
}

export default api

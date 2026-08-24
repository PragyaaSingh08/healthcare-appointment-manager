import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import { ToastProvider } from './components/Toast'
import AppLayout from './layouts/AppLayout'

import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import VerifyEmail from './pages/VerifyEmail'
import PatientDashboard from './pages/patient/PatientDashboard'
import DoctorSearch from './pages/patient/DoctorSearch'
import DoctorProfile from './pages/patient/DoctorProfile'
import AppointmentList from './pages/patient/AppointmentList'
import AppointmentDetail from './pages/patient/AppointmentDetail'
import ChatAssistant from './pages/patient/ChatAssistant'
import DoctorAppointmentList from './pages/doctor/DoctorAppointmentList'
import ConsultationView from './pages/doctor/ConsultationView'
import AdminOverview from './pages/admin/AdminOverview'
import AdminDoctors from './pages/admin/AdminDoctors'
import type { Role } from './types'

function ProtectedByRole({ allow, children }: { allow: Role[]; children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-8 text-ink-400">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  if (!allow.includes(user.role)) return <Navigate to="/" replace />
  return <>{children}</>
}

function RoleHome() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (user.role === 'PATIENT') return <Navigate to="/patient" replace />
  if (user.role === 'DOCTOR') return <Navigate to="/doctor" replace />
  return <Navigate to="/admin" replace />
}

export default function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />

        <Route element={<AppLayout />}>
          <Route path="/" element={<RoleHome />} />

          <Route
            path="/patient"
            element={
              <ProtectedByRole allow={['PATIENT']}>
                <PatientDashboard />
              </ProtectedByRole>
            }
          />
          <Route
            path="/patient/doctors"
            element={
              <ProtectedByRole allow={['PATIENT']}>
                <DoctorSearch />
              </ProtectedByRole>
            }
          />
          <Route
            path="/patient/doctors/:id"
            element={
              <ProtectedByRole allow={['PATIENT']}>
                <DoctorProfile />
              </ProtectedByRole>
            }
          />
          <Route
            path="/patient/appointments"
            element={
              <ProtectedByRole allow={['PATIENT']}>
                <AppointmentList />
              </ProtectedByRole>
            }
          />
          <Route
            path="/patient/appointments/:id"
            element={
              <ProtectedByRole allow={['PATIENT']}>
                <AppointmentDetail />
              </ProtectedByRole>
            }
          />
          <Route
            path="/patient/chat"
            element={
              <ProtectedByRole allow={['PATIENT']}>
                <ChatAssistant />
              </ProtectedByRole>
            }
          />

          <Route
            path="/doctor"
            element={
              <ProtectedByRole allow={['DOCTOR']}>
                <DoctorAppointmentList todayOnly />
              </ProtectedByRole>
            }
          />
          <Route
            path="/doctor/appointments"
            element={
              <ProtectedByRole allow={['DOCTOR']}>
                <DoctorAppointmentList />
              </ProtectedByRole>
            }
          />
          <Route
            path="/doctor/appointments/:id"
            element={
              <ProtectedByRole allow={['DOCTOR']}>
                <ConsultationView />
              </ProtectedByRole>
            }
          />

          <Route
            path="/admin"
            element={
              <ProtectedByRole allow={['ADMIN']}>
                <AdminOverview />
              </ProtectedByRole>
            }
          />
          <Route
            path="/admin/doctors"
            element={
              <ProtectedByRole allow={['ADMIN']}>
                <AdminDoctors />
              </ProtectedByRole>
            }
          />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ToastProvider>
  )
}

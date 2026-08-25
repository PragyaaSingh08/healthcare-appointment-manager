import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authApi, apiErrorMessage } from '../services/api'
import CalendarConnectButton from '../components/CalendarConnectButton'

const NAV_BY_ROLE: Record<string, { to: string; label: string }[]> = {
  PATIENT: [
    { to: '/patient', label: 'Dashboard' },
    { to: '/patient/doctors', label: 'Find a doctor' },
    { to: '/patient/appointments', label: 'My appointments' },
    { to: '/patient/chat', label: 'Assistant' },
  ],
  DOCTOR: [
    { to: '/doctor', label: 'Today' },
    { to: '/doctor/appointments', label: 'All appointments' },
  ],
  ADMIN: [
    { to: '/admin', label: 'Overview' },
    { to: '/admin/doctors', label: 'Doctors' },
  ],
}

function VerificationBanner() {
  const { user } = useAuth()
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!user || user.is_email_verified) return null

  async function resend() {
    setError(null)
    try {
      await authApi.resendVerification()
      setSent(true)
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  return (
    <div className="bg-amber-100 text-amber-600 text-sm px-6 py-2 flex items-center justify-between">
      <span>Please verify your email address.</span>
      {sent ? (
        <span className="font-medium">Verification email sent.</span>
      ) : (
        <button onClick={resend} className="font-medium underline underline-offset-2">
          {error ? 'Try again' : 'Resend verification email'}
        </button>
      )}
    </div>
  )
}

export default function AppLayout() {
  const { user, logout } = useAuth()
  const nav = user ? NAV_BY_ROLE[user.role] ?? [] : []
  const showCalendarSync = user && (user.role === 'PATIENT' || user.role === 'DOCTOR')

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 shrink-0 bg-forest-900 text-white flex flex-col">
        <div className="px-6 py-6 border-b border-white/10">
          <p className="font-display text-xl leading-none">Meridian</p>
          <p className="text-xs text-white/60 mt-1 tracking-wide uppercase">Clinic Appointments</p>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end
              className={({ isActive }) =>
                `block rounded-card px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? 'bg-white/10 text-white' : 'text-white/70 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        {showCalendarSync && (
          <div className="px-4 py-3 border-t border-white/10">
            <CalendarConnectButton compact className="w-full justify-center" />
          </div>
        )}
        <div className="px-6 py-4 border-t border-white/10">
          <p className="text-sm text-white/80">{user?.name}</p>
          <p className="text-xs text-white/50 mb-3">{user?.role.toLowerCase()}</p>
          <button onClick={logout} className="text-xs text-white/70 hover:text-white underline underline-offset-2">
            Sign out
          </button>
        </div>
      </aside>
      <div className="flex-1 flex flex-col">
        <VerificationBanner />
        <main className="flex-1 bg-canvas">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

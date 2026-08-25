import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { calendarApi, apiErrorMessage } from '../services/api'
import { useAuth } from '../context/AuthContext'

type Status = 'processing' | 'success' | 'error'

export default function CalendarCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [status, setStatus] = useState<Status>('processing')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const code = searchParams.get('code')
  const state = searchParams.get('state')
  const statusParam = searchParams.get('status')
  const messageParam = searchParams.get('message')
  const errorParam = searchParams.get('error')
  const errorDescParam = searchParams.get('error_description')

  useEffect(() => {
    // 1. Direct status redirect from backend
    if (statusParam === 'success') {
      setStatus('success')
      const timeout = setTimeout(() => {
        const redirectPath = user?.role === 'DOCTOR' ? '/doctor' : '/patient'
        navigate(redirectPath)
      }, 3000)
      return () => clearTimeout(timeout)
    }

    if (statusParam === 'error' || errorParam) {
      setStatus('error')
      setErrorMessage(messageParam || errorDescParam || errorParam || 'Google authorization was denied or failed.')
      return
    }

    // 2. Authorization code exchange
    if (!code || !state) {
      setStatus('error')
      setErrorMessage('Missing OAuth authorization code or state parameter from Google.')
      return
    }

    let isMounted = true

    async function handleExchange() {
      try {
        await calendarApi.callback(code!, state!)
        if (isMounted) {
          setStatus('success')
          setTimeout(() => {
            const redirectPath = user?.role === 'DOCTOR' ? '/doctor' : '/patient'
            navigate(redirectPath)
          }, 3000)
        }
      } catch (err) {
        if (isMounted) {
          setStatus('error')
          setErrorMessage(apiErrorMessage(err))
        }
      }
    }

    handleExchange()

    return () => {
      isMounted = false
    }
  }, [code, state, statusParam, messageParam, errorParam, errorDescParam, navigate, user])

  const targetDashboard = user?.role === 'DOCTOR' ? '/doctor' : '/patient'

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-6">
      <div className="card p-8 max-w-md w-full text-center space-y-6 shadow-sm border border-forest-100">
        {status === 'processing' && (
          <div className="space-y-4 py-4">
            <div className="w-12 h-12 border-4 border-forest-200 border-t-forest-700 rounded-full animate-spin mx-auto" />
            <h1 className="font-display text-2xl text-forest-900">Connecting Google Calendar</h1>
            <p className="text-sm text-ink-400">
              Please wait while we complete the authorization with Google…
            </p>
          </div>
        )}

        {status === 'success' && (
          <div className="space-y-4 py-4">
            <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center text-2xl mx-auto">
              ✓
            </div>
            <h1 className="font-display text-2xl text-emerald-900">Google Calendar Connected</h1>
            <p className="text-sm text-ink-700">
              Your calendar is now connected. Your appointments and follow-up reminders will sync automatically.
            </p>
            <p className="text-xs text-ink-400">Redirecting to dashboard in a moment…</p>
            <div className="pt-2">
              <Link to={targetDashboard} className="btn-primary inline-block w-full">
                Go to Dashboard
              </Link>
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-4 py-4">
            <div className="w-12 h-12 rounded-full bg-clay-100 text-clay-500 flex items-center justify-center text-2xl mx-auto">
              ✕
            </div>
            <h1 className="font-display text-2xl text-clay-500">Connection Failed</h1>
            <p className="text-sm text-ink-700">
              {errorMessage || 'Google Calendar connection was cancelled or could not be completed.'}
            </p>
            <div className="pt-2 space-y-2">
              <Link to={targetDashboard} className="btn-primary inline-block w-full">
                Return to Dashboard
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { calendarApi, apiErrorMessage } from '../services/api'
import { useToast } from './Toast'

interface CalendarConnectButtonProps {
  compact?: boolean
  className?: string
}

export default function CalendarConnectButton({ compact = false, className = '' }: CalendarConnectButtonProps) {
  const { show } = useToast()
  const [connected, setConnected] = useState<boolean | null>(null)
  const [connecting, setConnecting] = useState(false)

  useEffect(() => {
    calendarApi
      .status()
      .then((res) => setConnected(res.data.connected))
      .catch(() => setConnected(false))
  }, [])

  async function handleConnect() {
    setConnecting(true)
    try {
      const { data } = await calendarApi.connect()
      if (data.auth_url) {
        window.location.href = data.auth_url
      } else {
        show('Unable to get Google Calendar authorization URL.', 'error')
        setConnecting(false)
      }
    } catch (err) {
      show(apiErrorMessage(err), 'error')
      setConnecting(false)
    }
  }

  if (connected === null) {
    return null // Still loading initial status
  }

  if (connected) {
    if (compact) {
      return (
        <span
          className={`inline-flex items-center gap-1.5 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2.5 py-1 ${className}`}
          title="Google Calendar is connected. Appointments sync automatically."
        >
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
          Calendar Synced
        </span>
      )
    }

    return (
      <div className={`card p-5 border border-emerald-200 bg-emerald-50/50 flex items-center justify-between ${className}`}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700 font-bold text-sm">
            📅
          </div>
          <div>
            <p className="font-medium text-emerald-900 text-sm">Google Calendar Connected</p>
            <p className="text-xs text-emerald-700">
              Appointments, reschedules, and cancellations sync automatically to your calendar.
            </p>
          </div>
        </div>
        <span className="text-xs font-medium text-emerald-800 bg-emerald-100 rounded-full px-2.5 py-1">
          Active
        </span>
      </div>
    )
  }

  if (compact) {
    return (
      <button
        onClick={handleConnect}
        disabled={connecting}
        className={`inline-flex items-center gap-1.5 text-xs font-medium text-forest-700 hover:text-forest-900 bg-forest-50 hover:bg-forest-100 border border-forest-200 rounded-card px-3 py-1.5 transition-colors ${className}`}
      >
        <span>📅</span>
        {connecting ? 'Connecting…' : 'Sync Calendar'}
      </button>
    )
  }

  return (
    <div className={`card p-5 border border-forest-100 flex items-center justify-between ${className}`}>
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-forest-50 flex items-center justify-center text-forest-700 text-base">
          📅
        </div>
        <div>
          <p className="font-medium text-ink-900 text-sm">Google Calendar Sync</p>
          <p className="text-xs text-ink-400">
            Connect your calendar to get real-time appointment invites and automatic updates.
          </p>
        </div>
      </div>
      <button
        onClick={handleConnect}
        disabled={connecting}
        className="btn-secondary text-xs px-3.5 py-1.5 shrink-0"
      >
        {connecting ? 'Connecting…' : 'Connect Google Calendar'}
      </button>
    </div>
  )
}

import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { authApi, apiErrorMessage } from '../services/api'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const navigate = useNavigate()

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (newPassword !== confirmPassword) {
      setError("Passwords don't match.")
      return
    }
    if (!token) {
      setError('This reset link is missing its token. Please request a new one.')
      return
    }
    setSubmitting(true)
    try {
      await authApi.resetPassword(token, newPassword)
      setDone(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <p className="font-display text-3xl text-forest-900">Meridian</p>
          <p className="text-ink-400 text-sm mt-1">Choose a new password</p>
        </div>

        {!token && (
          <div className="card p-6 text-center">
            <p className="text-sm text-clay-500 mb-4">This reset link is invalid or incomplete.</p>
            <Link to="/forgot-password" className="text-forest-700 font-medium text-sm">
              Request a new link
            </Link>
          </div>
        )}

        {token && done && (
          <div className="card p-6 text-center">
            <p className="text-sm text-ink-900 mb-2">Your password has been reset.</p>
            <p className="text-xs text-ink-400">Redirecting you to sign in…</p>
          </div>
        )}

        {token && !done && (
          <form onSubmit={onSubmit} className="card p-6 space-y-4">
            {error && <p className="text-clay-500 text-sm bg-clay-500/10 rounded-card px-3 py-2">{error}</p>}
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">New password</label>
              <input
                className="input"
                type="password"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
              <p className="text-xs text-ink-400 mt-1">At least 8 characters.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">Confirm new password</label>
              <input
                className="input"
                type="password"
                required
                minLength={8}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </div>
            <button type="submit" disabled={submitting} className="btn-primary w-full">
              {submitting ? 'Resetting…' : 'Reset password'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

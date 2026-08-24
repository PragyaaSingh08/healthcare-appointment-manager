import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { authApi, apiErrorMessage } from '../services/api'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await authApi.forgotPassword(email)
      // Always shown regardless of whether the email is registered — the
      // backend deliberately returns an identical response either way.
      setSubmitted(true)
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
          <p className="text-ink-400 text-sm mt-1">Reset your password</p>
        </div>

        {submitted ? (
          <div className="card p-6 text-center">
            <p className="text-sm text-ink-900 mb-4">
              If an account with that email exists, we've sent a password reset link to <strong>{email}</strong>.
            </p>
            <Link to="/login" className="text-forest-700 font-medium text-sm">
              Back to sign in
            </Link>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="card p-6 space-y-4">
            {error && <p className="text-clay-500 text-sm bg-clay-500/10 rounded-card px-3 py-2">{error}</p>}
            <p className="text-sm text-ink-400">Enter your account email and we'll send you a link to reset your password.</p>
            <div>
              <label className="block text-sm font-medium text-ink-700 mb-1">Email</label>
              <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <button type="submit" disabled={submitting} className="btn-primary w-full">
              {submitting ? 'Sending…' : 'Send reset link'}
            </button>
            <p className="text-center text-sm">
              <Link to="/login" className="text-forest-700 font-medium">
                Back to sign in
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}

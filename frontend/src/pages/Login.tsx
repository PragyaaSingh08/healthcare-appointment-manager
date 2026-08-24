import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiErrorMessage } from '../services/api'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      navigate('/')
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
          <p className="text-ink-400 text-sm mt-1">Sign in to manage your appointments</p>
        </div>
        <form onSubmit={onSubmit} className="card p-6 space-y-4">
          {error && <p className="text-clay-500 text-sm bg-clay-500/10 rounded-card px-3 py-2">{error}</p>}
          <div>
            <label className="block text-sm font-medium text-ink-700 mb-1">Email</label>
            <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium text-ink-700 mb-1">Password</label>
            <input
              className="input"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <div className="text-right mt-1">
              <Link to="/forgot-password" className="text-xs text-forest-700 hover:underline">
                Forgot password?
              </Link>
            </div>
          </div>
          <button type="submit" disabled={submitting} className="btn-primary w-full">
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p className="text-center text-sm text-ink-400 mt-4">
          New patient?{' '}
          <Link to="/register" className="text-forest-700 font-medium">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  )
}

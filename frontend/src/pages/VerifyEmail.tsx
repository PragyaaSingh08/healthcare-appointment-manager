import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { authApi, apiErrorMessage } from '../services/api'

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setError('This verification link is missing its token.')
      return
    }
    authApi
      .verifyEmail(token)
      .then(() => setStatus('success'))
      .catch((err) => {
        setStatus('error')
        setError(apiErrorMessage(err))
      })
  }, [token])

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-sm text-center">
        <p className="font-display text-3xl text-forest-900 mb-8">Meridian</p>
        <div className="card p-6">
          {status === 'verifying' && <p className="text-sm text-ink-400">Verifying your email…</p>}
          {status === 'success' && (
            <>
              <p className="text-sm text-ink-900 mb-4">Your email has been verified.</p>
              <Link to="/" className="btn-primary inline-block">
                Continue
              </Link>
            </>
          )}
          {status === 'error' && (
            <>
              <p className="text-sm text-clay-500 mb-4">{error || 'This verification link is invalid or has expired.'}</p>
              <Link to="/" className="text-forest-700 font-medium text-sm">
                Go to dashboard
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

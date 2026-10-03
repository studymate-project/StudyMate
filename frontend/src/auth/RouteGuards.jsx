import { Navigate, useLocation } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import { useAuth } from './useAuth'

function AuthLoading() {
  return <main className="flex min-h-[calc(100svh-4rem)] items-center justify-center bg-[var(--color-band)] px-4 text-center text-[var(--color-text)]"><p role="status">Checking your session…</p></main>
}

function AuthError({ error, onRetry }) {
  return (
    <main className="flex min-h-[calc(100svh-4rem)] items-center justify-center bg-[var(--color-band)] px-4 text-center text-[var(--color-text)]">
      <div className="max-w-md space-y-4">
        <p role="alert">{getApiErrorMessage(error)}</p>
        <button type="button" onClick={onRetry} className="min-h-11 border border-[var(--color-primary-light)] px-5 text-sm font-semibold text-[var(--color-primary-light)] hover:bg-[var(--color-primary-soft)]">Try again</button>
      </div>
    </main>
  )
}

export function ProtectedRoute({ children }) {
  const location = useLocation()
  const { status, error, retryInitialization } = useAuth()

  if (status === 'loading') return <AuthLoading />
  if (status === 'error') return <AuthError error={error} onRetry={retryInitialization} />
  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />
  }

  return children
}

export function PublicOnlyRoute({ children }) {
  const { status, user } = useAuth()
  if (status === 'authenticated') {
    return <Navigate to={user?.profile?.onboarding_completed ? '/home' : '/onboarding'} replace />
  }
  return children
}

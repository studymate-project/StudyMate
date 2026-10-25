import { Mail } from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { getApiErrorMessage, getApiFieldErrors } from '../api/errors'
import { useAuth } from '../auth/useAuth'
import { getPostAuthDestination } from '../auth/navigation'
import AuthDivider from '../components/auth/AuthDivider'
import AuthInput from '../components/auth/AuthInput'
import AuthLayout from '../components/auth/AuthLayout'
import GoogleAuthButton from '../components/auth/GoogleAuthButton'
import PasswordInput from '../components/auth/PasswordInput'

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function Login() {
  const location = useLocation()
  const navigate = useNavigate()
  const { signIn } = useAuth()
  const [form, setForm] = useState({ email: '', password: '', remember: false })
  const [errors, setErrors] = useState({})
  const [notice, setNotice] = useState(() => location.state?.notice || '')
  const [noticeIsError, setNoticeIsError] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const update = (event) => {
    const { name, value, checked, type } = event.target
    setForm((current) => ({ ...current, [name]: type === 'checkbox' ? checked : value }))
    if (errors[name]) setErrors((current) => ({ ...current, [name]: '' }))
    setNotice('')
    setNoticeIsError(false)
  }

  const handleLogin = async (event) => {
    event.preventDefault()
    const nextErrors = {}
    if (!form.email.trim()) nextErrors.email = 'Please enter your email address.'
    else if (!emailPattern.test(form.email)) nextErrors.email = 'Please enter a valid email address.'
    if (!form.password) nextErrors.password = 'Please enter your password.'
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) return

    setIsSubmitting(true)
    setNotice('')
    try {
      const result = await signIn({ email: form.email.trim(), password: form.password })
      const destination = getPostAuthDestination(result.user, location.state?.from)
      navigate(destination, { replace: true, state: null })
    } catch (error) {
      const fieldErrors = getApiFieldErrors(error)
      setErrors((current) => ({ ...current, ...fieldErrors }))
      setNotice(getApiErrorMessage(error))
      setNoticeIsError(true)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthLayout variant="login">
      <article className="w-full max-w-[422px] border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-6 sm:p-9">
        <p className="text-base font-semibold text-[var(--color-primary-light)]">StudyMate</p>
        <h2 className="mt-1 text-2xl font-bold leading-tight text-white">Welcome back</h2>
        <p className="mt-2 text-sm font-normal text-[var(--color-text)]">Continue your learning journey.</p>
        <div className="my-5 h-0.5 bg-[var(--color-border-strong)]" />
        <form noValidate onSubmit={handleLogin} className="space-y-4">
          <AuthInput id="login-email" name="email" label="Email Address" icon={Mail} type="email" placeholder="you@example.com" autoComplete="email" value={form.email} onChange={update} error={errors.email} />
          <PasswordInput id="login-password" name="password" placeholder="••••••••" autoComplete="current-password" value={form.password} onChange={update} error={errors.password} />
          <div className="flex items-start justify-between gap-4 pt-0.5">
            <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-[var(--color-text)]">
              <input name="remember" type="checkbox" checked={form.remember} onChange={update} className="h-4 w-4 accent-[var(--color-primary)]" />
              Remember me
            </label>
            <button type="button" onClick={() => { setNotice('Password recovery is not available yet.'); setNoticeIsError(false) }} className="text-right text-sm font-medium text-[var(--color-primary-light)] underline decoration-1 underline-offset-4 transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]">Forgot Password?</button>
          </div>
          <button type="submit" disabled={isSubmitting} className="min-h-11 w-full rounded-xl bg-[var(--color-primary)] px-4 text-base font-semibold text-white transition-colors hover:bg-[var(--color-primary-hover)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60">{isSubmitting ? 'Logging in…' : 'Log In'}</button>
          {notice ? <p role={noticeIsError ? 'alert' : 'status'} className={noticeIsError ? 'rounded-lg border border-[var(--color-danger)] bg-[color-mix(in_srgb,var(--color-danger)_12%,var(--color-surface))] px-3 py-2 text-center text-xs font-normal leading-5 text-[var(--color-danger)]' : 'rounded-lg border border-[var(--color-border)] bg-[var(--color-primary-soft)] px-3 py-2 text-center text-xs font-normal leading-5 text-[var(--color-text)]'}>{notice}</p> : null}
          <AuthDivider />
          <GoogleAuthButton onClick={() => { setNotice('Google authentication is not available yet.'); setNoticeIsError(false) }} />
        </form>
        <p className="mt-4 text-center text-xs font-normal text-[var(--color-text)]">Don&apos;t have an account?</p>
        <Link to="/signup" className="mx-auto mt-3 block w-fit text-sm font-medium text-[var(--color-primary-light)] underline decoration-1 underline-offset-4 transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]">Sign Up</Link>
      </article>
    </AuthLayout>
  )
}

export default Login

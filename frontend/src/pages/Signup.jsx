import { Mail, UserRound } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getApiErrorMessage, getApiFieldErrors } from '../api/errors'
import { useAuth } from '../auth/useAuth'
import AuthDivider from '../components/auth/AuthDivider'
import AuthInput from '../components/auth/AuthInput'
import AuthLayout from '../components/auth/AuthLayout'
import GoogleAuthButton from '../components/auth/GoogleAuthButton'
import PasswordInput from '../components/auth/PasswordInput'

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const initialForm = { name: '', email: '', password: '', college: '', country: '', state: '', city: '' }

function Signup() {
  const navigate = useNavigate()
  const { signIn, signUp } = useAuth()
  const [form, setForm] = useState(initialForm)
  const [errors, setErrors] = useState({})
  const [notice, setNotice] = useState('')
  const [noticeIsError, setNoticeIsError] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const update = (event) => {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
    if (errors[name]) setErrors((current) => ({ ...current, [name]: '' }))
    setNotice('')
    setNoticeIsError(false)
  }

  const handleSignup = async (event) => {
    event.preventDefault()
    const nextErrors = {}
    if (!form.name.trim()) nextErrors.name = 'This field is required.'
    if (!form.email.trim()) nextErrors.email = 'Please enter your email address.'
    else if (!emailPattern.test(form.email)) nextErrors.email = 'Please enter a valid email address.'
    if (!form.password) nextErrors.password = 'This field is required.'
    if (!form.college.trim()) nextErrors.college = 'This field is required.'
    if (!form.country.trim()) nextErrors.country = 'This field is required.'
    if (!form.state.trim()) nextErrors.state = 'This field is required.'
    if (!form.city.trim()) nextErrors.city = 'This field is required.'
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) return

    setIsSubmitting(true)
    setNotice('')
    try {
      const credentials = { email: form.email.trim(), password: form.password }
      await signUp({
        name: form.name.trim(),
        email: credentials.email,
        password: form.password,
        college: form.college.trim(),
        country: form.country.trim(),
        state: form.state.trim(),
        city: form.city.trim(),
      })
      const result = await signIn(credentials)
      navigate(result.user?.profile?.onboarding_completed ? '/home' : '/onboarding', { replace: true })
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
    <AuthLayout variant="signup">
      <article className="w-full max-w-[462px] border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-6 sm:p-8">
        <p className="text-base font-semibold text-[var(--color-primary-light)]">StudyMate</p>
        <h2 className="mt-1 text-xl font-bold leading-tight text-white">Join StudyMate</h2>
        <p className="mt-1 text-sm font-normal text-[var(--color-text)]">Learn, share and grow with students like you.</p>
        <div className="my-4 h-0.5 bg-[var(--color-border-strong)]" />
        <form noValidate onSubmit={handleSignup} className="space-y-3.5">
          <AuthInput id="signup-name" name="name" label="Full Name" icon={UserRound} placeholder="Rahul Sharma" autoComplete="name" value={form.name} onChange={update} error={errors.name} />
          <AuthInput id="signup-email" name="email" label="Email Address" icon={Mail} type="email" placeholder="rahul@example.com" autoComplete="email" value={form.email} onChange={update} error={errors.email} />
          <PasswordInput id="signup-password" name="password" placeholder="Create a password" autoComplete="new-password" value={form.password} onChange={update} error={errors.password} />
          <AuthInput id="signup-college" name="college" label="College / University" placeholder="IIT Delhi" value={form.college} onChange={update} error={errors.college} />
          <div className="grid gap-3 sm:grid-cols-3">
            <AuthInput id="signup-country" name="country" label="Country" placeholder="India" value={form.country} onChange={update} error={errors.country} />
            <AuthInput id="signup-state" name="state" label="State" placeholder="Delhi" value={form.state} onChange={update} error={errors.state} />
            <AuthInput id="signup-city" name="city" label="City" placeholder="New Delhi" value={form.city} onChange={update} error={errors.city} />
          </div>
          <button type="submit" disabled={isSubmitting} className="min-h-11 w-full bg-[var(--color-primary)] px-4 text-base font-semibold text-white transition-colors hover:bg-[var(--color-primary-hover)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)] disabled:cursor-not-allowed disabled:opacity-60">{isSubmitting ? 'Creating account…' : 'Create Account'}</button>
          {notice ? <p role={noticeIsError ? 'alert' : 'status'} className={noticeIsError ? 'border border-red-300 bg-red-950/40 px-3 py-2 text-center text-xs font-normal leading-5 text-red-100' : 'border border-[var(--color-primary-light)] bg-[var(--color-primary-soft)] px-3 py-2 text-center text-xs font-normal leading-5 text-slate-100'}>{notice}</p> : null}
          <AuthDivider />
          <GoogleAuthButton onClick={() => { setNotice('Google authentication is not available yet.'); setNoticeIsError(false) }} />
        </form>
        <p className="mt-4 text-center text-xs font-normal text-[var(--color-text)]">Already have an account?</p>
        <Link to="/login" className="mx-auto mt-3 block w-fit text-sm font-medium text-[var(--color-primary-light)] underline decoration-1 underline-offset-4 transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]">Log In</Link>
      </article>
    </AuthLayout>
  )
}

export default Signup

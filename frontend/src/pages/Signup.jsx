import { ArrowLeft, Mail, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { requestSignupVerification, verifySignupEmail } from '../api/auth'
import { getApiErrorMessage, getApiFieldErrors } from '../api/errors'
import { useAuth } from '../auth/useAuth'
import AuthDivider from '../components/auth/AuthDivider'
import AuthInput from '../components/auth/AuthInput'
import AuthLayout from '../components/auth/AuthLayout'
import GoogleAuthButton from '../components/auth/GoogleAuthButton'
import PasswordInput from '../components/auth/PasswordInput'

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
// This mirrors the backend's default cooldown. The backend remains authoritative.
const resendCooldownSeconds = 60
const initialForm = { name: '', email: '', password: '', college: '', country: '', state: '', city: '' }

function getFriendlyError(error) {
  if (error?.status === 429) return 'Too many requests. Please wait a moment and try again.'
  if (error?.code === 'ERR_NETWORK') return 'We could not reach StudyMate. Check your connection and try again.'
  return getApiErrorMessage(error)
}

function Signup() {
  const navigate = useNavigate()
  const { signUp } = useAuth()
  const [form, setForm] = useState(initialForm)
  const [errors, setErrors] = useState({})
  const [step, setStep] = useState('signup')
  const [otp, setOtp] = useState('')
  const [otpError, setOtpError] = useState('')
  const [notice, setNotice] = useState('')
  const [noticeIsError, setNoticeIsError] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isVerifying, setIsVerifying] = useState(false)
  const [isResending, setIsResending] = useState(false)
  const [resendCooldown, setResendCooldown] = useState(0)

  useEffect(() => {
    if (resendCooldown <= 0) return undefined
    const timer = window.setTimeout(() => setResendCooldown((current) => Math.max(current - 1, 0)), 1000)
    return () => window.clearTimeout(timer)
  }, [resendCooldown])

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
    else if (!emailPattern.test(form.email.trim())) nextErrors.email = 'Please enter a valid email address.'
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
      const result = await signUp({
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
        college: form.college.trim(),
        country: form.country.trim(),
        state: form.state.trim(),
        city: form.city.trim(),
      })

      if (result.status === 202) {
        setStep('verification')
        setOtp('')
        setOtpError('')
        setResendCooldown(resendCooldownSeconds)
        setNotice('If this email is eligible, a verification code will be sent. Enter it below to activate your account.')
        setNoticeIsError(false)
      }
    } catch (error) {
      if (error?.status === 503) {
        // The account may have committed before the broker failure surfaced.
        // Keep the existing verification UI available so the user can retry
        // through the resend endpoint once delivery is available again.
        setStep('verification')
        setOtp('')
        setOtpError('')
        setResendCooldown(0)
        setNotice('We could not send the verification email. Please try Resend code again.')
        setNoticeIsError(true)
        return
      }
      const fieldErrors = getApiFieldErrors(error)
      setErrors((current) => ({ ...current, ...fieldErrors }))
      setNotice(getFriendlyError(error))
      setNoticeIsError(true)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleOtpChange = (event) => {
    const digits = event.target.value.replace(/\D/g, '').slice(0, 6)
    setOtp(digits)
    setOtpError('')
    setNotice('')
    setNoticeIsError(false)
  }

  const handleVerify = async (event) => {
    event.preventDefault()
    if (!/^\d{6}$/.test(otp)) {
      setOtpError('Enter the 6-digit verification code.')
      return
    }

    setIsVerifying(true)
    setOtpError('')
    setNotice('')
    try {
      const result = await verifySignupEmail({ email: form.email.trim(), code: otp })
      if (result.status === 200) {
        navigate('/login', {
          replace: true,
          state: { notice: 'Email verified successfully. You can now log in.' },
        })
      }
    } catch (error) {
      setOtpError(getFriendlyError(error))
    } finally {
      setIsVerifying(false)
    }
  }

  const handleResend = async () => {
    if (isResending || resendCooldown > 0) return

    setIsResending(true)
    setOtpError('')
    setNotice('')
    try {
      const result = await requestSignupVerification({ email: form.email.trim() })
      if (result.status === 202) {
        setResendCooldown(resendCooldownSeconds)
        setNotice('Your request was accepted. If this email is eligible, a new verification code will be sent.')
        setNoticeIsError(false)
      }
    } catch (error) {
      setNotice(getFriendlyError(error))
      setNoticeIsError(true)
    } finally {
      setIsResending(false)
    }
  }

  const handleEditEmail = () => {
    if (isVerifying || isResending) return
    setStep('signup')
    setOtp('')
    setOtpError('')
    setNotice('')
    setNoticeIsError(false)
  }

  return (
    <AuthLayout variant="signup">
      <article className="w-full max-w-[462px] border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-6 sm:p-8">
        <p className="text-base font-semibold text-[var(--color-primary-light)]">StudyMate</p>
        {step === 'signup' ? (
          <>
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
              <button type="submit" disabled={isSubmitting} className="min-h-11 w-full rounded-xl bg-[var(--color-primary)] px-4 text-base font-semibold text-white transition-colors hover:bg-[var(--color-primary-hover)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60">{isSubmitting ? 'Creating account...' : 'Create Account'}</button>
              {notice ? <p role={noticeIsError ? 'alert' : 'status'} aria-live="polite" className={noticeIsError ? 'rounded-lg border border-[var(--color-danger)] bg-[color-mix(in_srgb,var(--color-danger)_12%,var(--color-surface))] px-3 py-2 text-center text-xs font-normal leading-5 text-[var(--color-danger)]' : 'rounded-lg border border-[var(--color-border)] bg-[var(--color-primary-soft)] px-3 py-2 text-center text-xs font-normal leading-5 text-[var(--color-text)]'}>{notice}</p> : null}
              <AuthDivider />
              <GoogleAuthButton onClick={() => { setNotice('Google authentication is not available yet.'); setNoticeIsError(false) }} />
            </form>
          </>
        ) : (
          <>
            <h2 className="mt-1 text-xl font-bold leading-tight text-white">Verify your email</h2>
            <p className="mt-1 text-sm font-normal leading-6 text-[var(--color-text)]">Enter the 6-digit code sent to <span className="font-semibold text-white">{form.email.trim()}</span>.</p>
            <div className="my-4 h-0.5 bg-[var(--color-border-strong)]" />
            <form noValidate onSubmit={handleVerify} className="space-y-3.5">
              <div>
                <label htmlFor="signup-otp" className="mb-1.5 block text-sm font-medium text-[var(--color-text)]">Verification code</label>
                <input
                  id="signup-otp"
                  name="code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]*"
                  maxLength={6}
                  autoFocus
                  value={otp}
                  onChange={handleOtpChange}
                  aria-invalid={Boolean(otpError)}
                  aria-describedby={otpError ? 'signup-otp-error' : undefined}
                  className="h-12 w-full rounded-xl border border-[var(--color-border-strong)] bg-[var(--color-surface-alt)] px-4 text-center text-xl font-semibold tracking-[0.45em] text-white outline-none transition-colors placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-primary-light)] focus:ring-2 focus:ring-[var(--color-focus)]"
                  placeholder="000000"
                />
                {otpError ? <p id="signup-otp-error" className="mt-1.5 text-xs leading-5 text-[var(--color-danger)]" role="alert">{otpError}</p> : null}
              </div>
              <button type="submit" disabled={isVerifying || otp.length !== 6} className="min-h-11 w-full rounded-xl bg-[var(--color-primary)] px-4 text-base font-semibold text-white transition-colors hover:bg-[var(--color-primary-hover)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60">{isVerifying ? 'Verifying...' : 'Verify email'}</button>
              {notice ? <p role={noticeIsError ? 'alert' : 'status'} aria-live="polite" className={noticeIsError ? 'rounded-lg border border-[var(--color-danger)] bg-[color-mix(in_srgb,var(--color-danger)_12%,var(--color-surface))] px-3 py-2 text-center text-xs font-normal leading-5 text-[var(--color-danger)]' : 'rounded-lg border border-[var(--color-border)] bg-[var(--color-primary-soft)] px-3 py-2 text-center text-xs font-normal leading-5 text-[var(--color-text)]'}>{notice}</p> : null}
              <button type="button" onClick={handleResend} disabled={isResending || resendCooldown > 0} className="mx-auto block text-sm font-medium text-[var(--color-primary-light)] underline decoration-1 underline-offset-4 transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)] disabled:cursor-not-allowed disabled:opacity-50">{isResending ? 'Requesting new code...' : resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : 'Resend code'}</button>
            </form>
            <button type="button" onClick={handleEditEmail} disabled={isVerifying || isResending} className="mx-auto mt-5 flex items-center gap-1.5 text-xs font-medium text-[var(--color-text)] transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)] disabled:cursor-not-allowed disabled:opacity-50"><ArrowLeft size={14} aria-hidden="true" />Edit signup details</button>
          </>
        )}
        <p className="mt-4 text-center text-xs font-normal text-[var(--color-text)]">Already have an account?</p>
        <Link to="/login" className="mx-auto mt-3 block w-fit text-sm font-medium text-[var(--color-primary-light)] underline decoration-1 underline-offset-4 transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]">Log In</Link>
      </article>
    </AuthLayout>
  )
}

export default Signup

import { Eye, EyeOff, LockKeyhole } from 'lucide-react'
import { useState } from 'react'

function PasswordInput({ id, label = 'Password', error, ...props }) {
  const [visible, setVisible] = useState(false)
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-[var(--color-text)]">{label}</label>
      <div className="relative">
        <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-dim)]" size={17} aria-hidden="true" />
        <input id={id} type={visible ? 'text' : 'password'} className={`auth-control pl-10 pr-11 ${error ? 'border-[var(--color-danger)] focus:border-[var(--color-danger)]' : ''}`} aria-invalid={error ? 'true' : undefined} aria-describedby={error ? `${id}-error` : undefined} {...props} />
        <button type="button" onClick={() => setVisible((current) => !current)} aria-label={visible ? 'Hide password' : 'Show password'} className="absolute right-1 top-1/2 inline-flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-lg text-[var(--color-text-dim)] transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-focus)]">
          {visible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
        </button>
      </div>
      {error ? <p id={`${id}-error`} className="mt-1 text-xs font-normal text-[var(--color-danger)]">{error}</p> : null}
    </div>
  )
}

export default PasswordInput

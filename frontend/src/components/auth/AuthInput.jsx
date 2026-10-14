function AuthInput({ id, label, icon: Icon, error, className = '', ...props }) {
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-[var(--color-text)]">{label}</label>
      <div className="relative">
        {Icon ? <Icon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-dim)]" size={18} aria-hidden="true" /> : null}
        <input id={id} className={`auth-control ${Icon ? 'pl-10' : ''} ${error ? 'border-[var(--color-danger)] focus:border-[var(--color-danger)]' : ''}`} aria-invalid={error ? 'true' : undefined} aria-describedby={error ? `${id}-error` : undefined} {...props} />
      </div>
      {error ? <p id={`${id}-error`} className="mt-1 text-xs font-normal text-[var(--color-danger)]">{error}</p> : null}
    </div>
  )
}

export default AuthInput

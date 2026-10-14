const variants = {
  blue: 'border-[var(--color-primary)] bg-[var(--color-primary-soft)] text-[var(--color-primary-light)]',
  purple: 'border-[var(--color-purple)] bg-[var(--color-purple-soft)] text-[var(--color-purple)]',
  teal: 'border-[var(--color-teal)] bg-[var(--color-teal-soft)] text-[var(--color-teal)]',
  gray: 'border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text)]',
  outline: 'border-[var(--color-border-strong)] bg-transparent text-[var(--color-text)]',
  dark: 'border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text)]',
  orange: 'border-[var(--color-warning)] bg-[color-mix(in_srgb,var(--color-warning)_12%,var(--color-surface))] text-[var(--color-warning)]',
}

function Badge({ children, variant = 'blue', className = '' }) {
  return (
    <span className={`inline-flex min-h-6 items-center rounded-lg border px-2.5 text-sm font-black leading-none ${variants[variant]} ${className}`}>
      {children}
    </span>
  )
}

export default Badge

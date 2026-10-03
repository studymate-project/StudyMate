import { Link } from 'react-router-dom'

const variants = {
  primary: 'border-[var(--color-primary)] bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-hover)]',
  secondary: 'border-[var(--color-primary-light)] bg-transparent text-[var(--color-primary-light)] hover:bg-[var(--color-primary-soft)] hover:text-white',
  dark: 'border-[var(--color-border)] bg-[var(--color-surface-muted)] text-white hover:border-[var(--color-primary-light)]',
}

function Button({ children, to, variant = 'primary', className = '', type = 'button', ...props }) {
  const classes = [
    'inline-flex min-h-11 items-center justify-center gap-2 border px-5 py-2 text-base font-black leading-none transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)] disabled:cursor-not-allowed disabled:opacity-60',
    variants[variant],
    className,
  ].join(' ')

  if (to) {
    return (
      <Link to={to} className={classes}>
        {children}
      </Link>
    )
  }

  return (
    <button type={type} className={classes} {...props}>
      {children}
    </button>
  )
}

export default Button

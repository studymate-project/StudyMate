function IconButton({ children, label, variant = 'default', className = '', ...props }) {
  const variants = {
    default: 'border-transparent text-[var(--color-text)] hover:border-[var(--color-border)] hover:text-white',
    primary: 'border-[var(--color-primary-dark)] bg-[var(--color-primary-dark)] text-[var(--color-primary-light)] hover:bg-[var(--color-primary)] hover:text-white',
  }

  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={[
        'inline-flex h-10 w-10 items-center justify-center border transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] disabled:cursor-not-allowed disabled:opacity-60',
        variants[variant],
        className,
      ].join(' ')}
      {...props}
    >
      {children}
    </button>
  )
}

export default IconButton

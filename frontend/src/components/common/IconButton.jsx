function IconButton({ children, label, variant = 'default', className = '', ...props }) {
  const variants = {
    default: 'border-transparent text-[var(--color-text)] hover:border-[var(--color-border)] hover:text-[var(--color-primary-light)]',
    primary: 'border-[var(--color-primary)] bg-[var(--color-primary-soft)] text-[var(--color-primary-light)] hover:bg-[var(--color-surface-hover)] hover:text-white',
  }

  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={[
        'inline-flex h-10 w-10 items-center justify-center rounded-lg border transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60',
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

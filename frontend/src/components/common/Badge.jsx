const variants = {
  blue: 'border-[#1f87d0] bg-[#0a5f9c] text-white',
  purple: 'border-[#5f3be2] bg-[#4020b6] text-white',
  teal: 'border-[#14a591] bg-[#007f70] text-white',
  gray: 'border-[#93a3ae] bg-[#718391] text-[#162532]',
  outline: 'border-[var(--color-border-strong)] bg-transparent text-[var(--color-text)]',
  dark: 'border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text)]',
  orange: 'border-[#d97816] bg-[#bd5908] text-white',
}

function Badge({ children, variant = 'blue', className = '' }) {
  return (
    <span className={`inline-flex min-h-6 items-center rounded-full border px-2.5 text-sm font-black leading-none ${variants[variant]} ${className}`}>
      {children}
    </span>
  )
}

export default Badge

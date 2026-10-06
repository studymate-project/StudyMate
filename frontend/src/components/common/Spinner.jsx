function Spinner({ label = 'Loading', tone = 'default', className = '' }) {
  const toneClass = tone === 'muted' ? 'text-slate-700' : 'text-[var(--color-primary-light)]'

  return <span role="status" aria-label={label} className={`inline-block h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent ${toneClass} ${className}`} />
}

export default Spinner

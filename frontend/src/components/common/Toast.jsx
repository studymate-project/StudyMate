function Toast({ message, type = 'success', onDismiss }) {
  if (!message) return null
  const styles = type === 'error'
    ? 'border-[var(--color-danger)] bg-[color-mix(in_srgb,var(--color-danger)_14%,var(--color-surface))] text-[var(--color-danger)]'
    : 'border-[var(--color-success)] bg-[color-mix(in_srgb,var(--color-success)_14%,var(--color-surface))] text-[var(--color-success)]'

  return <div role="status" className={`fixed bottom-5 right-5 z-50 flex max-w-sm items-center gap-4 border px-4 py-3 text-sm font-semibold shadow-md ${styles}`}><span>{message}</span><button type="button" aria-label="Dismiss message" onClick={onDismiss} className="text-lg leading-none">×</button></div>
}

export default Toast

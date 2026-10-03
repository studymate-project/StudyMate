function Toast({ message, type = 'success', onDismiss }) {
  if (!message) return null
  const styles = type === 'error'
    ? 'border-[#d86c75] bg-[#4b1e2b] text-[#ffe1e5]'
    : 'border-[#19a99a] bg-[#073f3a] text-[#d9fffa]'

  return <div role="status" className={`fixed bottom-5 right-5 z-50 flex max-w-sm items-center gap-4 border px-4 py-3 text-sm font-semibold shadow-lg ${styles}`}><span>{message}</span><button type="button" aria-label="Dismiss message" onClick={onDismiss} className="text-lg leading-none">×</button></div>
}

export default Toast

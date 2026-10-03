import { useNavigate } from 'react-router-dom'

function NotificationItem({ notification, onRead }) {
  const navigate = useNavigate()
  const openNotification = async () => {
    const readSucceeded = await onRead(notification.id)
    if (readSucceeded && notification.target) navigate(notification.target)
  }
  return <article className={`flex gap-3 border-2 p-3 transition-colors sm:items-center sm:p-4 ${notification.unread ? 'border-[#0878c9] bg-[#063c68]' : 'border-[var(--color-border)] bg-[var(--color-surface-muted)] hover:border-[var(--color-border-strong)]'}`}><span aria-hidden="true" className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white ${notification.actor.color}`}>{notification.actor.initials}</span><div className="min-w-0 flex-1"><p className="text-sm font-semibold text-white">{notification.message}</p><p className="mt-1 text-xs text-[var(--color-text)]">{notification.time}</p></div><button type="button" onClick={openNotification} className="min-h-8 shrink-0 border border-[var(--color-border-strong)] px-4 text-xs font-semibold text-[var(--color-text)] hover:border-white hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]">View</button></article>
}

export default NotificationItem

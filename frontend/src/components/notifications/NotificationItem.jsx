import { useNavigate } from 'react-router-dom'
import { openNotificationTarget } from '../../api/notifications'

function NotificationItem({ notification, onRead }) {
  const navigate = useNavigate()
  const openNotification = async () => {
    const readSucceeded = await onRead(notification.id)
    if (readSucceeded) openNotificationTarget(notification, navigate)
  }
  return <article className={`flex gap-3 border-2 p-3 transition-colors sm:items-center sm:p-4 ${notification.unread ? 'border-[var(--color-info)] bg-[var(--color-surface)]' : 'border-[var(--color-border)] bg-[var(--color-surface-muted)] hover:border-[var(--color-border-strong)]'}`}><span aria-hidden="true" className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-[var(--color-text)] ${notification.actor.color}`}>{notification.actor.initials}</span><div className="min-w-0 flex-1"><p className="text-sm font-semibold text-white">{notification.message}</p><p className="mt-1 text-xs text-[var(--color-text)]">{notification.time}</p></div>{notification.target ? <button type="button" onClick={openNotification} className="min-h-8 shrink-0 rounded-lg border border-[var(--color-border)] px-4 text-xs font-semibold text-[var(--color-text)] hover:border-[var(--color-focus)] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]">{notification.targetKind === 'external' ? 'Open link' : 'View'}</button> : <div className="flex shrink-0 items-center gap-2"><span className="text-xs font-semibold text-[var(--color-text-dim)]" aria-label="Notification target unavailable">Unavailable</span><button type="button" onClick={openNotification} className="min-h-8 rounded-lg border border-[var(--color-border)] px-3 text-xs font-semibold text-[var(--color-text)] hover:border-[var(--color-focus)] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]">Mark read</button></div>}</article>
}

export default NotificationItem

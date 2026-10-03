import NotificationItem from './NotificationItem'

function NotificationGroup({ title, notifications, onRead }) {
  if (!notifications.length) return null
  return <section className="mt-5"><h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--color-text)]">{title}</h2><div className="space-y-2">{notifications.map((notification) => <NotificationItem key={notification.id} notification={notification} onRead={onRead} />)}</div></section>
}

export default NotificationGroup

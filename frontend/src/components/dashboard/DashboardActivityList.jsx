import { Bookmark, ChevronRight } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'

export function RecentNotifications({ notifications }) {
  const navigate = useNavigate()
  return <DashboardSection title="Recent notifications" to="/notifications">{notifications.length ? notifications.map((notification) => <button type="button" onClick={() => notification.target && navigate(notification.target)} key={notification.id} className="flex w-full items-start gap-3 border-b border-[var(--color-border)] px-3 py-3 text-left last:border-b-0 hover:bg-[var(--color-surface-muted)]"><span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-[#0878c9]" /><span><span className="block text-xs font-medium text-white">{notification.message}</span><span className="mt-1 block text-xs text-[var(--color-text)]">{notification.time}</span></span></button>) : <p className="px-3 py-4 text-xs text-[var(--color-text)]">No recent notifications.</p>}</DashboardSection>
}

export function RecentSaves({ resources }) {
  return <DashboardSection title="Recent saves" to="/saved">{resources.map((resource) => <Link key={resource.id} to={`/resources/${resource.slug}`} className="flex items-center justify-between gap-3 border-b border-[var(--color-border)] px-3 py-3 last:border-b-0 hover:bg-[var(--color-surface-muted)]"><span className="text-xs font-medium text-white">{resource.title}</span><Bookmark size={16} className="shrink-0 text-[#55b7ee]" /></Link>)}</DashboardSection>
}

function DashboardSection({ title, to, children }) { return <section><div className="mb-2 flex items-center justify-between"><h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text)]">{title}</h2><Link to={to} className="inline-flex items-center text-xs font-semibold text-[#55b7ee] hover:text-white">View all <ChevronRight size={14} /></Link></div><div className="border-2 border-[var(--color-border)] bg-[var(--color-surface)]">{children}</div></section> }

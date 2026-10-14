function DashboardStats({ stats }) {
  return <section className="overflow-hidden border-2 border-[var(--color-border)] bg-[var(--color-surface)]">{stats.map((stat) => <article key={stat.label} className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3 last:border-b-0"><span className="text-sm font-semibold text-white">{stat.label}</span><strong className="text-sm font-semibold text-[var(--color-text)]">{stat.value}</strong></article>)}</section>
}

export default DashboardStats

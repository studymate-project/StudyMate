function WeeklyActivity({ items }) {
  const highest = Math.max(...items.map((item) => item.value))
  return <section><h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text)]">Weekly activity</h2><div className="mt-3 grid h-40 grid-cols-7 items-end gap-2 rounded-xl bg-[var(--color-band)] px-3 pb-3 pt-4 sm:gap-4 sm:px-6">{items.map((item) => <div key={item.day} className="flex h-full min-w-0 flex-col items-center justify-end gap-1"><div className={`${item.day === 'Thu' ? 'bg-[var(--color-primary)]' : 'bg-[var(--color-surface-muted)]'} w-full max-w-6 rounded-t`} style={{ height: `${Math.max(16, item.value / highest * 100)}%` }} title={`${item.day}: ${item.duration}`} /><span className="text-xs font-medium text-white">{item.day}</span><span className="text-[11px] text-[var(--color-text)]">{item.duration}</span></div>)}</div></section>
}

export default WeeklyActivity

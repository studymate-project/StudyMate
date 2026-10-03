function ResourceStats({ stats }) {
  if (!stats.length) return null

  return (
    <section className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:max-w-[520px]" aria-label="Resource statistics">
      {stats.map((stat) => (
        <article key={stat.label} className="bg-[var(--color-band)] px-4 py-5 text-center">
          <p className="text-3xl font-black leading-none text-white">{stat.value}</p>
          <p className="mt-3 text-sm font-black text-[var(--color-text)]">{stat.label}</p>
        </article>
      ))}
    </section>
  )
}

export default ResourceStats

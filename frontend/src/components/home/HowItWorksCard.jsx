function HowItWorksCard({ step }) {
  const { Icon } = step

  return (
    <article className="min-h-[225px] border-2 border-[var(--color-border)] bg-transparent p-6">
      <p className="text-3xl font-black text-[var(--color-primary-light)]">{step.number}</p>
      <Icon className="mt-6 text-[var(--color-primary-light)]" size={34} strokeWidth={1.8} />
      <h3 className="mt-5 text-lg font-black text-white">{step.title}</h3>
      <p className="mt-3 text-sm font-black leading-snug text-white/90">{step.description}</p>
    </article>
  )
}

export default HowItWorksCard

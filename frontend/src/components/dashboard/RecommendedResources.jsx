import { Link } from 'react-router-dom'

function RecommendedResources({ resources }) {
  return <section><h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text)]">Recommended for you</h2><div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{resources.map((resource) => <article key={resource.title} className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-3"><h3 className="text-sm font-semibold text-white">{resource.title}</h3><span className="mt-3 inline-flex rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2 py-0.5 text-xs font-medium text-[var(--color-text)]">{resource.subject}</span><Link to={resource.route} className="mt-3 flex min-h-9 items-center justify-center rounded-lg border border-[var(--color-border)] text-sm font-semibold text-[var(--color-text)] hover:bg-[var(--color-surface-muted)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]">View</Link></article>)}</div></section>
}

export default RecommendedResources

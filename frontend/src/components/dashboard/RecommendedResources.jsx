import { Link } from 'react-router-dom'

function RecommendedResources({ resources }) {
  return <section><h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text)]">Recommended for you</h2><div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{resources.map((resource) => <article key={resource.title} className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-3"><h3 className="text-sm font-semibold text-white">{resource.title}</h3><span className="mt-3 inline-flex rounded-full border border-[#2585c0] px-2 py-0.5 text-xs font-medium text-[#55b7ee]">{resource.subject}</span><Link to={resource.route} className="mt-3 flex min-h-9 items-center justify-center border border-[#2585c0] text-sm font-semibold text-[#55b7ee] hover:bg-[#073c68] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]">View</Link></article>)}</div></section>
}

export default RecommendedResources

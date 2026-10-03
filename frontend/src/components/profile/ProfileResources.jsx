import { Link } from 'react-router-dom'

function ProfileResources({ resources, title = 'Recent resources', empty = 'No resources shared yet.' }) {
  if (!resources.length) return <p className="border-2 border-[var(--color-border)] p-5 text-sm text-[var(--color-text)]">{empty}</p>
  return <section><h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text)]">{title}</h2><div className="mt-3 space-y-3">{resources.map((resource) => <article key={resource.id} className="flex flex-col gap-3 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 sm:flex-row sm:items-center sm:justify-between"><div><h3 className="text-sm font-semibold text-white">{resource.title}</h3><div className="mt-2 flex flex-wrap gap-2"><span className="rounded-full border border-[#2585c0] px-2 py-0.5 text-xs text-[#55b7ee]">{resource.subject}</span><span className="rounded-full border border-[var(--color-border-strong)] px-2 py-0.5 text-xs text-[var(--color-text)]">{resource.type}</span></div></div><Link to={`/resources/${resource.slug}`} className="inline-flex min-h-9 items-center justify-center border border-[#2585c0] px-5 text-sm font-semibold text-[#55b7ee] hover:bg-[#073c68]">View</Link></article>)}</div></section>
}

export default ProfileResources

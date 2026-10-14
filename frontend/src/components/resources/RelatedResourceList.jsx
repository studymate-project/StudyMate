import { ChevronRight, FileText } from 'lucide-react'
import { Link } from 'react-router-dom'

function RelatedResourceList({ resources }) {
  if (!resources.length) return null

  return (
    <aside className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="text-base font-black text-white">Related Resources</h2>
      <div className="mt-4 h-px bg-[var(--color-border-strong)]" />
      <div className="mt-3 space-y-3">
        {resources.map((resource) => (
          <Link
            key={resource.id || resource.title}
            to={`/resources/${resource.slug}`}
            className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border-2 border-[var(--color-border)] p-3 transition-colors hover:border-[var(--color-primary-light)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
          >
            <FileText size={21} className="text-[var(--color-text)]" />
            <div className="min-w-0">
              <h3 className="text-sm font-black leading-tight text-white">{resource.title}</h3>
              <p className="text-sm font-black text-[var(--color-text)]">{resource.type}</p>
            </div>
            <ChevronRight size={22} className="text-[var(--color-text)]" />
          </Link>
        ))}
      </div>
    </aside>
  )
}

export default RelatedResourceList

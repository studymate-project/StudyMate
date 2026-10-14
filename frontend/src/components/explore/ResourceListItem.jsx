import { FileText } from 'lucide-react'
import { Link } from 'react-router-dom'
import { formatNumber, getUserById } from '../../data/dataHelpers'
import Button from '../common/Button'
import Rating from '../common/Rating'

function ResourceListItem({ resource }) {
  const author = resource.author || getUserById(resource.authorId)

  return (
    <article className="grid gap-4 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center">
      <Link
        to={`/resources/${resource.slug}`}
        className="flex min-w-0 items-center gap-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
      >
        <div className={`${resource.colorClass} flex h-12 w-12 shrink-0 items-center justify-center rounded-lg text-[var(--color-primary-light)]`}>
          <FileText size={22} />
        </div>
        <div className="min-w-0">
          <h3 className="truncate text-base font-black text-white sm:text-lg">{resource.title}</h3>
          <p className="mt-1 text-sm font-black text-[var(--color-text)]">
            {resource.type} <span aria-hidden="true">-</span> by {author?.name}
          </p>
        </div>
      </Link>

      <div className="flex flex-wrap items-center gap-4 text-sm font-black sm:justify-end">
        <Rating value={resource.rating} count={resource.ratingCount} />
        <span className="text-[var(--color-text)]">{formatNumber(resource.downloads ?? 0)} Downloads</span>
      </div>

      <Button to={`/resources/${resource.slug}`} className="w-full px-6 sm:w-auto">
        View
      </Button>
    </article>
  )
}

export default ResourceListItem

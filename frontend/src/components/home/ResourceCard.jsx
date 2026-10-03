import { FileText, Star } from 'lucide-react'
import { Link } from 'react-router-dom'
import { formatNumber, getUserById } from '../../data/dataHelpers'

function ResourceCard({ resource }) {
  const author = resource.author || getUserById(resource.authorId)

  return (
    <Link
      to={`/resources/${resource.slug}`}
      className="block min-h-[250px] border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 transition-colors hover:border-[var(--color-primary-light)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
    >
      <div className={`${resource.colorClass} flex h-14 w-14 items-center justify-center text-[var(--color-primary-light)]`}>
        <FileText size={25} />
      </div>
      <h3 className="mt-5 min-h-[48px] text-lg font-black leading-tight text-white">{resource.title}</h3>
      <p className="mt-2 text-sm font-black text-[var(--color-text)]">by {author?.name}</p>
      <div className="mt-4 flex flex-wrap items-center gap-2 text-sm font-black">
        <Star size={16} className="fill-[var(--color-star)] text-[var(--color-star)]" />
        <span className="text-white">{resource.rating ?? 'N/A'}</span>
        <span className="text-[var(--color-text)]">+</span>
        <span className="text-[var(--color-text)]">{resource.views == null ? 'Views unavailable' : `${formatNumber(resource.views)} Views`}</span>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {resource.tags.slice(0, 2).map((tag) => (
          <span key={tag} className="bg-[var(--color-chip)] px-3 py-2 text-base font-black leading-none text-white">
            #{tag}
          </span>
        ))}
      </div>
    </Link>
  )
}

export default ResourceCard

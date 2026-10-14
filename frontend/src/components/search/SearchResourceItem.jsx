import { Bookmark } from 'lucide-react'
import Badge from '../common/Badge'
import Rating from '../common/Rating'

function SearchResourceItem({ resource }) {
  return (
    <article className="relative border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 pr-11">
      <button type="button" aria-label={`Save ${resource.title}`} className="absolute right-4 top-4 text-[var(--color-text)]">
        <Bookmark size={18} className="fill-current" />
      </button>
      <h3 className="text-base font-black text-white">{resource.title}</h3>
      <div className="mt-2 flex flex-wrap gap-2">
        {resource.badges.map((badge, index) => (
          <Badge key={badge} variant={index === 0 ? 'blue' : 'outline'}>
            {badge}
          </Badge>
        ))}
      </div>
      <p className="mt-4 text-sm font-black text-[var(--color-text)]">Uploaded by {resource.author}</p>
      <div className="mt-3 flex flex-wrap gap-5">
        <Rating value={resource.rating} />
        <span className="text-sm font-black text-[var(--color-text)]">{resource.downloads}</span>
        <span className="text-sm font-black text-[var(--color-text)]">{resource.saves}</span>
      </div>
    </article>
  )
}

export default SearchResourceItem

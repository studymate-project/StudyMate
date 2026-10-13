import { Bookmark, Trash2 } from 'lucide-react'
import Badge from '../common/Badge'
import Button from '../common/Button'
import Rating from '../common/Rating'

function SavedResourceItem({ resource }) {
  return (
    <article className="grid gap-4 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
      <div className="min-w-0">
        <h3 className="break-words text-lg font-black text-white">{resource.title}</h3>
        <div className="mt-2 flex flex-wrap gap-2">
          <Badge variant="blue">{resource.category}</Badge>
          <Badge variant="outline">{resource.type}</Badge>
        </div>
        <p className="mt-3 text-sm font-black text-[var(--color-text)]">by {resource.author}</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Rating value={resource.rating} count={resource.ratingCount} showValue={false} />
          <span className="text-sm font-black text-[var(--color-text)]">{resource.views}</span>
        </div>
      </div>

      <div className="flex flex-col items-stretch gap-12 md:items-end">
        <div className="flex justify-end gap-3">
          <button type="button" aria-label={`Bookmark ${resource.title}`} className="text-[#58a7df]">
            <Bookmark size={18} className="fill-current" />
          </button>
          <button type="button" aria-label={`Remove ${resource.title}`} className="text-[var(--color-text)] hover:text-white">
            <Trash2 size={19} />
          </button>
        </div>
        <Button to="/resources/java-oop-complete-notes" className="bg-[var(--color-blue)] hover:bg-[var(--color-blue-hover)]">
          Open Resource
        </Button>
      </div>
    </article>
  )
}

export default SavedResourceItem

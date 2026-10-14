import { PlayCircle } from 'lucide-react'

function SearchVideoItem({ video }) {
  return (
    <article className="grid gap-4 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 sm:grid-cols-[96px_minmax(0,1fr)] sm:items-center">
      <div className="flex h-16 items-center justify-center rounded-lg bg-[var(--color-surface-muted)] text-[var(--color-text)]">
        <PlayCircle size={25} />
      </div>
      <div className="min-w-0">
        <h3 className="text-base font-black text-white">{video.title}</h3>
        <p className="mt-1 text-sm font-black text-[var(--color-text)]">
          {video.duration} <span className="mx-2">{video.views}</span>
        </p>
      </div>
    </article>
  )
}

export default SearchVideoItem

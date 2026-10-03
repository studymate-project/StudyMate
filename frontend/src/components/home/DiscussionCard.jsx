import { MessageSquare, Triangle } from 'lucide-react'
import { Link } from 'react-router-dom'

function DiscussionCard({ discussion }) {
  const author = discussion.author

  return (
    <Link
      to={`/questions/${discussion.slug}`}
      className="block border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 transition-colors hover:border-[var(--color-primary-light)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
    >
      <div className="flex h-10 w-10 items-center justify-center bg-[#260777] text-[var(--color-primary-light)]">
        <MessageSquare size={18} />
      </div>
      <h3 className="mt-5 min-h-[52px] text-base font-black leading-snug text-white">{discussion.title}</h3>
      <p className="mt-3 text-sm font-black text-[var(--color-text)]">Asked by {author?.name || 'StudyMate member'}</p>
      <div className="mt-4 flex flex-wrap items-center gap-5 text-sm font-black">
        <span className="text-white">{discussion.answerCount}</span>
        <span className="inline-flex items-center gap-1 text-[var(--color-success)]">
          <Triangle size={12} className="fill-current" />
          {discussion.upvotes ?? 0}
        </span>
      </div>
    </Link>
  )
}

export default DiscussionCard

import { Triangle } from 'lucide-react'

function SearchQuestionItem({ question }) {
  return (
    <article className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <h3 className="text-base font-black text-white">{question.title}</h3>
      <div className="mt-3 flex flex-wrap gap-5 text-sm font-black">
        <span className="inline-flex items-center gap-1 text-[var(--color-text)]">
          <Triangle size={12} className="fill-current" />
          {question.upvotes}
        </span>
        <span className="text-[var(--color-text)]">{question.answers}</span>
      </div>
    </article>
  )
}

export default SearchQuestionItem

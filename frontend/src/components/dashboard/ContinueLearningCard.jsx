import Button from '../common/Button'

function ContinueLearningCard({ learning }) {
  return <section className="border border-[var(--color-border)] bg-[var(--color-surface)] p-5 sm:p-6">
    <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-dim)]">Continue learning</p>
    <h2 className="mt-3 text-lg font-semibold text-white">{learning.title}</h2>
    <p className="mt-3 text-sm font-medium text-[var(--color-text-dim)]">{learning.progress}% Complete</p>
    <div className="mt-2 h-2 overflow-hidden rounded-full bg-[var(--color-border)]"><div className="h-full bg-[var(--color-primary)]" style={{ width: `${learning.progress}%` }} /></div>
    <Button to={learning.route} variant="dark" className="mt-4 w-full">Continue Learning</Button>
  </section>
}

export default ContinueLearningCard

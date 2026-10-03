import Button from '../common/Button'

function ContinueLearningCard({ learning }) {
  return <section className="border border-[#075b96] bg-[#063d69] p-5 sm:p-6">
    <p className="text-xs font-semibold uppercase tracking-wide text-[#a8d9f8]">Continue learning</p>
    <h2 className="mt-3 text-lg font-semibold text-white">{learning.title}</h2>
    <p className="mt-3 text-sm font-medium text-[#b4d8ed]">{learning.progress}% Complete</p>
    <div className="mt-2 h-2 overflow-hidden bg-[#61798a]"><div className="h-full bg-[var(--color-blue)]" style={{ width: `${learning.progress}%` }} /></div>
    <Button to={learning.route} className="mt-4 w-full bg-[var(--color-surface-muted)] hover:bg-[var(--color-band)]">Continue Learning</Button>
  </section>
}

export default ContinueLearningCard

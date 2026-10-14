import { Triangle } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getApiErrorMessage, listQuestions } from '../api'
import Button from '../components/common/Button'
import Spinner from '../components/common/Spinner'

const tabs = ['Latest', 'Trending', 'Unanswered', 'Popular']
const topics = ['Java', 'DSA', 'DBMS', 'OS', 'React', 'Python']

function Community() {
  const [activeTab, setActiveTab] = useState('Latest')
  const [questions, setQuestions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true
    listQuestions()
      .then(({ questions: nextQuestions }) => {
        if (!active) return
        setQuestions(nextQuestions)
        setError(null)
      })
      .catch((requestError) => {
        if (active) setError(getApiErrorMessage(requestError))
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
  }, [])

  const visibleQuestions = useMemo(() => {
    const list = [...questions]
    if (activeTab === 'Trending' || activeTab === 'Popular') return list.sort((a, b) => (b.upvotes || 0) - (a.upvotes || 0))
    if (activeTab === 'Unanswered') return list.filter((question) => question.answerCount === 0)
    return list
  }, [activeTab, questions])

  return (
    <div>
      <section className="bg-[var(--color-hero)] px-5 py-7 sm:px-8 lg:px-10">
        <div className="mx-auto flex max-w-[1260px] flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-black text-white">Student Community</h1>
            <p className="mt-2 font-black text-white/90">Ask questions, share knowledge, and learn together.</p>
          </div>
          <Button to="/community/ask" variant="dark">+ Ask a Question</Button>
        </div>
      </section>

      <div className="mx-auto grid max-w-[1260px] gap-7 px-5 py-5 sm:px-8 lg:grid-cols-[minmax(0,1fr)_310px] lg:px-10">
        <main className="min-w-0">
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Community question filters">
            {tabs.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`min-h-12 rounded-lg border px-5 font-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] ${activeTab === tab ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-primary-dark)]' : 'border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text)] hover:bg-[var(--color-blue-hover)]'}`}
              >
                {tab}
              </button>
            ))}
          </div>

          <section className="mt-4 space-y-3">
            {loading ? <div className="flex justify-center border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5"><Spinner label="Loading questions" /></div> : null}
            {!loading && error ? <p role="alert" className="border-2 border-[var(--color-danger)] bg-[color-mix(in_srgb,var(--color-danger)_12%,var(--color-surface))] p-5 font-black text-[var(--color-danger)]">{error}</p> : null}
            {!loading && !error && visibleQuestions.length === 0 ? <p className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 font-black text-[var(--color-text)]">No questions have been posted yet.</p> : null}
            {!loading && !error ? visibleQuestions.map((question) => <CommunityQuestionCard key={question.id} question={question} />) : null}
          </section>
        </main>

        <aside className="space-y-5">
          <section className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5">
            <h2 className="font-black text-white">Trending Topics</h2>
            <div className="mt-3 h-px bg-[var(--color-border-strong)]" />
            <div className="mt-3 flex flex-wrap gap-2">
              {topics.map((topic) => (
                <Link key={topic} to={`/explore?subject=${topic.toLowerCase()}`} className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-base font-black text-[var(--color-text)] hover:bg-[var(--color-blue-hover)]">
                  #{topic}
                </Link>
              ))}
            </div>
          </section>

        </aside>
      </div>
    </div>
  )
}

function CommunityQuestionCard({ question }) {
  const author = question.author

  return (
    <Link
      to={`/questions/${question.slug}`}
      className="grid gap-4 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 transition-colors hover:border-[var(--color-primary-light)] sm:grid-cols-[80px_minmax(0,1fr)_80px]"
    >
      <div className="border-r border-[var(--color-border)] pr-4 text-center sm:text-left">
        <p className="inline-flex items-center gap-1 text-2xl font-black text-[var(--color-success)]"><Triangle size={18} className="fill-current" />{question.upvotes ?? 0}</p>
        <p className="text-xs font-black text-[var(--color-text)]">votes</p>
      </div>
      <div className="min-w-0">
        <h2 className="break-words text-base font-black text-white">{question.title}</h2>
        <div className="mt-3 flex flex-wrap gap-2">{question.tags.map((tag) => <span key={tag} className="rounded-lg bg-[var(--color-primary)] px-3 py-1 font-black text-[var(--color-primary-dark)]">#{tag}</span>)}</div>
        <p className="mt-3 text-sm font-black text-[var(--color-text)]">Asked by {author?.name || 'StudyMate member'} - {question.createdAt || 'Date unavailable'}</p>
      </div>
      <div className="text-left sm:text-center">
        <p className="text-xl font-black text-white">{question.answerCount}</p>
        <p className="text-xs font-black text-[var(--color-text)]">answers</p>
      </div>
    </Link>
  )
}

export default Community

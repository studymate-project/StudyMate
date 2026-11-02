import { Triangle } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getApiErrorMessage } from '../api'
import { fetchQuestionList } from '../api/questions'
import Button from '../components/common/Button'
import Avatar from '../components/common/Avatar'
import QuestionDescription from '../components/community/QuestionDescription'
import { QuestionListSkeleton } from '../components/common/Skeletons'
import { QUERY_STALE_TIMES } from '../query/queryClient'
import { questionKeys } from '../query/queryKeys'

const tabs = ['Latest', 'Trending', 'Unanswered', 'Popular']

function Community() {
  const [activeTab, setActiveTab] = useState('Latest')
  const questionQuery = useQuery({
    queryKey: questionKeys.list({}),
    queryFn: () => fetchQuestionList({}),
    staleTime: QUERY_STALE_TIMES.lists,
  })
  const loading = questionQuery.isPending
  const error = questionQuery.error ? getApiErrorMessage(questionQuery.error) : null

  const visibleQuestions = useMemo(() => {
    const list = [...(questionQuery.data?.questions || [])]
    if (activeTab === 'Trending' || activeTab === 'Popular') return list.sort((a, b) => (b.upvotes || 0) - (a.upvotes || 0))
    if (activeTab === 'Unanswered') return list.filter((question) => question.answerCount === 0)
    return list
  }, [activeTab, questionQuery.data?.questions])

  return (
    <div>
      <section className="bg-[var(--color-hero)] py-7">
        <div className="site-container flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-black text-white">Student Community</h1>
            <p className="mt-2 font-black text-white/90">Ask questions, share knowledge, and learn together.</p>
          </div>
          <Button to="/community/ask" variant="dark">+ Ask a Question</Button>
        </div>
      </section>

      <div className="site-container grid gap-7 py-5 lg:grid-cols-[minmax(0,1fr)_310px]">
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
            {loading ? <QuestionListSkeleton /> : null}
            {!loading && error ? <p role="alert" className="border-2 border-[var(--color-danger)] bg-[color-mix(in_srgb,var(--color-danger)_12%,var(--color-surface))] p-5 font-black text-[var(--color-danger)]">{error}</p> : null}
            {!loading && !error && visibleQuestions.length === 0 ? <p className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 font-black text-[var(--color-text)]">No questions have been posted yet.</p> : null}
            {!loading && !error ? visibleQuestions.map((question) => <CommunityQuestionCard key={question.id} question={question} />) : null}
          </section>
        </main>
        
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
        <QuestionDescription description={question.body} className="relative mt-2" />
        <div className="mt-3 flex flex-wrap gap-2">{question.tags.map((tag) => <span key={tag} className="rounded-lg bg-[var(--color-primary)] px-3 py-1 font-black text-[var(--color-primary-dark)]">#{tag}</span>)}</div>
        <p className="mt-3 flex items-center gap-2 text-sm font-black text-[var(--color-text)]"><Avatar user={author} size="xs" decorative />Asked by {author?.name || 'StudyMate member'} - {question.createdAt || 'Date unavailable'}</p>
      </div>
      <div className="text-left sm:text-center">
        <p className="text-xl font-black text-white">{question.answerCount}</p>
        <p className="text-xs font-black text-[var(--color-text)]">answers</p>
      </div>
    </Link>
  )
}

export default Community

import { ThumbsUp } from 'lucide-react'
import { useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { createAnswer, getApiErrorMessage, removeAnswerUpvote, upvoteAnswer } from '../api'
import { fetchQuestionAnswers, fetchQuestionDetail } from '../api/questions'
import { getLoginState } from '../auth/navigation'
import { useAuth } from '../auth/useAuth'
import Button from '../components/common/Button'
import Avatar from '../components/common/Avatar'
import QuestionDescription from '../components/community/QuestionDescription'
import { QuestionDetailSkeleton } from '../components/common/Skeletons'
import { QUERY_STALE_TIMES } from '../query/queryClient'
import { questionKeys } from '../query/queryKeys'

function QuestionMessage({ title, message, showBackLink = true, loadingLabel = '' }) {
  if (loadingLabel) return <QuestionDetailSkeleton />

  return (
    <div className="mx-auto flex max-w-[900px] justify-center px-5 py-20 text-center">
      <div><h1 className="text-4xl font-black text-white">{title}</h1><p className="mt-4 font-bold text-[var(--color-text)]">{message}</p>{showBackLink ? <Button to="/community" className="mt-7">Back to Community</Button> : null}</div>
    </div>
  )
}

function QuestionDetailsView({ slug }) {
  const queryKey = slug || ''
  const location = useLocation()
  const navigate = useNavigate()
  const { status: authStatus } = useAuth()
  const questionQuery = useQuery({
    queryKey: questionKeys.detail(queryKey),
    queryFn: () => fetchQuestionDetail(queryKey),
    enabled: Boolean(queryKey),
    staleTime: QUERY_STALE_TIMES.details,
  })
  const question = questionQuery.data || null
  const answerQuery = useQuery({
    queryKey: questionKeys.answerList(question?.id ?? 'pending'),
    queryFn: () => fetchQuestionAnswers(question.id),
    enabled: Boolean(question?.id),
    staleTime: QUERY_STALE_TIMES.details,
  })
  const [addedAnswers, setAddedAnswers] = useState([])
  const [answerUpvoteOverrides, setAnswerUpvoteOverrides] = useState({})
  const [draft, setDraft] = useState('')
  const [preview, setPreview] = useState(false)
  const [posting, setPosting] = useState(false)
  const [actionError, setActionError] = useState(null)
  const [answerVoteState, setAnswerVoteState] = useState({})
  const answerRef = useRef(null)

  const loading = questionQuery.isPending || (Boolean(question) && answerQuery.isPending)
  const error = questionQuery.error || answerQuery.error
  const baseAnswers = answerQuery.data?.answers || []
  const baseAnswerIds = new Set(baseAnswers.map((answer) => answer.id))
  const answers = [...baseAnswers, ...addedAnswers.filter((answer) => !baseAnswerIds.has(answer.id))].map((answer) => (
    answerUpvoteOverrides[answer.id] === undefined
      ? answer
      : { ...answer, upvotes: answerUpvoteOverrides[answer.id] }
  ))
  const answerCount = (answerQuery.data?.count ?? question?.answerCount ?? 0)
    + addedAnswers.filter((answer) => !baseAnswerIds.has(answer.id)).length

  if (loading) return <QuestionMessage loadingLabel="Loading question" showBackLink={false} />
  if (error?.status === 404) return <QuestionMessage title="Question Not Found" message="This question may have been moved or removed." />
  if (error) return <QuestionMessage title="Unable to Load Question" message={getApiErrorMessage(error)} />
  if (!question) return <QuestionMessage title="Question Not Found" message="This question may have been moved or removed." />

  const postAnswer = async () => {
    const body = draft
    if (!body.trim() || posting) return
    if (authStatus !== 'authenticated') {
      navigate('/login', { state: getLoginState(location) })
      return
    }

    setPosting(true)
    setActionError(null)
    try {
      const answer = await createAnswer(question.id, body)
      setAddedAnswers((current) => [...current, answer])
      setDraft('')
      setPreview(false)
    } catch (requestError) {
      setActionError(getApiErrorMessage(requestError))
    } finally {
      setPosting(false)
    }
  }

  const toggleAnswerUpvote = async (answer) => {
    if (authStatus !== 'authenticated') {
      navigate('/login', { state: getLoginState(location) })
      return
    }
    const current = answerVoteState[answer.id] || { upvoted: null, pending: false }
    if (current.pending) return

    setAnswerVoteState((stateValue) => ({ ...stateValue, [answer.id]: { ...current, pending: true } }))
    setActionError(null)
    try {
      const result = current.upvoted
        ? await removeAnswerUpvote(question.id, answer.id)
        : await upvoteAnswer(question.id, answer.id)
      setAnswerVoteState((stateValue) => ({ ...stateValue, [answer.id]: { upvoted: result.upvoted, pending: false } }))
      setAnswerUpvoteOverrides((currentValues) => ({ ...currentValues, [answer.id]: result.upvotes }))
    } catch (requestError) {
      setAnswerVoteState((stateValue) => ({ ...stateValue, [answer.id]: { ...current, pending: false } }))
      setActionError(getApiErrorMessage(requestError))
    }
  }

  const focusAnswer = () => {
    answerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    answerRef.current?.focus()
  }

  const displayedQuestionUpvotes = question.upvotes == null ? 'N/A' : question.upvotes

  return (
    <div className="mx-auto w-full max-w-[1260px] px-5 py-6 sm:px-8 lg:px-10">
      <nav className="flex flex-wrap gap-2 text-sm font-black text-[var(--color-text)]" aria-label="Breadcrumb">
        <Link to="/community">Community</Link><span>/</span><Link to={`/explore?subject=${encodeURIComponent(question.subject.toLowerCase())}`}>{question.subject}</Link><span>/</span><span>{question.topic}</span><span>/</span><span className="text-[var(--color-primary-light)]">{question.title}</span>
      </nav>

      <div className="mt-5 grid gap-7 lg:grid-cols-[minmax(0,1fr)_310px]">
        <main className="min-w-0 space-y-5">
          <section className="p-5 sm:p-7">
            <h1 className="text-2xl font-black leading-tight text-white sm:text-3xl">{question.title}</h1>
            <div className="mt-4 flex flex-wrap gap-2">
              {question.tags.map((tag) => <span key={tag} className="rounded-lg bg-[var(--color-primary)] px-3 py-2 text-base font-black text-[var(--color-primary-dark)]">{tag}</span>)}
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-4 text-sm font-black text-[var(--color-text)]">
              {question.author?.username ? <Link to={`/users/${question.author.username}`} aria-label={`View ${question.author.name} profile`}><Avatar user={question.author} decorative /></Link> : <Avatar user={question.author} decorative />}
              {question.author?.username ? <Link to={`/users/${question.author.username}`} className="text-white">{question.author.name}</Link> : <span className="text-white">{question.author?.name || 'StudyMate member'}</span>}
              <span> {question.createdAt || 'Date unavailable'}</span>
              <span> {displayedQuestionUpvotes} Upvotes</span>
              <span> {answerCount} Answers</span>
            </div>
            <QuestionDescription description={question.body} className="relative mt-5 [&>p]:text-sm [&>p]:text-white/80" />
          </section>

          {actionError ? <p className="border border-[var(--color-danger)] bg-[color-mix(in_srgb,var(--color-danger)_12%,var(--color-surface))] p-3 text-sm font-black text-[var(--color-danger)]">{actionError}</p> : null}

          <h2 className="text-xl font-black text-white">{answerCount} Answers</h2>
          {answers.length
            ? answers.map((answer) => <AnswerCard key={answer.id} answer={answer} voteState={answerVoteState[answer.id]} onToggleVote={toggleAnswerUpvote} />)
            : <p className="p-1 text-sm font-black text-[var(--color-text)]">{answerCount ? 'No answers were returned for this question.' : 'No answers yet.'}</p>}

          <section className="p-3">
            <h2 className="font-black text-white">Write an Answer</h2>
            <textarea ref={answerRef} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Share your knowledge - be clear, concise, and helpful to other students." className="mt-3 min-h-28 w-full resize-y border-1 border-[var(--color-border-strong)] bg-[var(--color-surface)] p-4  text-white outline-none placeholder:text-[var(--color-text-dim)] focus:border-[var(--color-primary-light)]" />
            {preview && draft ? <div className="mt-3 whitespace-pre-wrap break-words border border-[var(--color-border)] bg-[var(--color-bg)] p-4 text-sm font-bold text-white">{draft}</div> : null}
            <div className="mt-3 flex flex-wrap gap-2">
              <Button onClick={postAnswer} disabled={posting || !draft.trim()}>{posting ? 'Posting...' : 'Post Answer'}</Button>
              <Button variant="dark" onClick={() => setPreview((value) => !value)}>Preview</Button>
            </div>
          </section>
        </main>

        <aside className="space-y-5">
          <section className="bg-[var(--color-primary-dark)] p-5">
            <h2 className="font-black text-white">Know the answer?</h2>
            <p className="mt-3 text-sm font-black text-white/90">Help fellow students by sharing what you know.</p>
            <Button variant="dark" className="mt-4 w-full" onClick={focusAnswer}>Write an Answer</Button>
          </section>
        </aside>
      </div>
    </div>
  )
}

function AnswerCard({ answer, voteState, onToggleVote }) {
  const author = answer.author
  const currentVoteState = voteState || { upvoted: null, pending: false }
  const upvoteLabel = answer.upvotes == null ? 'Upvote' : `${answer.upvotes} Upvotes`

  return (
    <article className=" p-5 sm:p-6">
      <div className="flex items-center gap-3">
        {author?.username ? <Link to={`/users/${author.username}`} aria-label={`View ${author.name} profile`}><Avatar user={author} decorative /></Link> : <Avatar user={author} decorative />}
        <div>
          {author?.username ? <Link to={`/users/${author.username}`} className="font-black text-white">{author.name}</Link> : <p className="font-black text-white">{author?.name || 'StudyMate member'}</p>}
          <p className="text-sm font-black text-[var(--color-text)]">{answer.createdAt || 'Date unavailable'}</p>
        </div>
      </div>
      <p className="mt-5 whitespace-pre-wrap break-words text-base font-black leading-relaxed text-white/90">{answer.body}</p>
      <div className="mt-5 flex flex-wrap gap-3">
        <Button variant="secondary" onClick={() => onToggleVote(answer)} disabled={currentVoteState.pending}><ThumbsUp size={18} />{currentVoteState.upvoted ? 'Upvoted' : upvoteLabel}</Button>
        {answer.isHelpful ? <span className="inline-flex min-h-11 items-center rounded-lg bg-[var(--color-surface-muted)] px-4 font-black text-[var(--color-text)]">Helpful Answer</span> : null}
      </div>
    </article>
  )
}

function QuestionDetails() {
  const { slug } = useParams()
  return <QuestionDetailsView key={slug} slug={slug} />
}

export default QuestionDetails

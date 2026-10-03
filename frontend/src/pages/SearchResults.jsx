import { Bookmark, Search, UserRound } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import Badge from '../components/common/Badge'
import Button from '../components/common/Button'
import SearchFilters from '../components/search/SearchFilters'
import SearchSection from '../components/search/SearchSection'
import { listQuestions } from '../api'
import { formatNumber, getUserById, searchAll } from '../data/dataHelpers'
import { searchFilters } from '../data/searchResults'

function SearchResults() {
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const initialQuery = searchParams.get('q') || 'java oop'
  const [query, setQuery] = useState(initialQuery)
  const [questionResults, setQuestionResults] = useState([])
  useEffect(() => {
    let active = true
    listQuestions({ search: initialQuery })
      .then(({ questions }) => { if (active) setQuestionResults(questions) })
      .catch(() => { if (active) setQuestionResults([]) })
    return () => { active = false }
  }, [initialQuery])
  const results = useMemo(() => ({ ...searchAll(initialQuery), questions: questionResults }), [initialQuery, questionResults])
  const resultCount = Object.values(results).reduce((sum, items) => sum + items.length, 0)

  const submit = (event) => {
    event.preventDefault()
    navigate(query.trim() ? `/search?q=${encodeURIComponent(query.trim())}` : '/search')
  }

  return (
    <div>
      <section className="bg-[var(--color-band)] px-5 py-8 sm:px-8 lg:px-10">
        <div className="mx-auto max-w-[1260px]">
          <form onSubmit={submit} className="grid gap-3 md:grid-cols-[minmax(0,1fr)_110px_100px]">
            <label className="relative min-w-0">
              <span className="sr-only">Search resources</span>
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-text)]" size={20} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} className="h-14 w-full border-2 border-[var(--color-border)] bg-[var(--color-surface)] pl-12 pr-4 text-base font-black text-white outline-none focus:border-[#58a7df]" />
            </label>
            <Button type="submit">Search</Button>
            <Button type="button" variant="secondary" onClick={() => { setQuery(''); navigate('/search') }}>Clear</Button>
          </form>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {(initialQuery ? initialQuery.split(' ') : ['All']).map((chip) => <Badge key={chip} variant="blue">{chip}</Badge>)}
            <span className="text-sm font-black text-[var(--color-text)]">Showing {resultCount} results for "{initialQuery || 'all'}"</span>
          </div>
        </div>
      </section>

      <div className="mx-auto grid max-w-[1260px] lg:grid-cols-[260px_minmax(0,1fr)]">
        <div className="border-b border-[var(--color-border)] p-4 lg:hidden">
          <button type="button" onClick={() => setFiltersOpen((open) => !open)} className="h-11 w-full border-2 border-[var(--color-border-strong)] text-base font-black text-white">
            {filtersOpen ? 'Hide Filters' : 'Show Filters'}
          </button>
        </div>
        <div className={filtersOpen ? 'block' : 'hidden lg:block'}><SearchFilters groups={searchFilters} /></div>

        <section className="min-w-0 px-5 py-7 sm:px-8">
          <SearchSection title="Resources">{results.resources.map((resource) => <ResourceResult key={resource.id} resource={resource} />)}</SearchSection>
          <SearchSection title="Videos">{results.videos.map((video) => <VideoResult key={video.id} video={video} />)}</SearchSection>
          <SearchSection title="Questions">{results.questions.map((question) => <QuestionResult key={question.id} question={question} />)}</SearchSection>
          <SearchSection title="Users"><div className="grid gap-3 sm:grid-cols-2">{results.users.map((user) => <UserResult key={user.id} user={user} />)}</div></SearchSection>
        </section>
      </div>
    </div>
  )
}

function ResultShell({ to, children }) {
  return <Link to={to} className="relative block border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 pr-11 transition-colors hover:border-[var(--color-primary-light)]">{children}</Link>
}

function ResourceResult({ resource }) {
  const author = getUserById(resource.authorId)
  return <ResultShell to={`/resources/${resource.slug}`}><Bookmark className="absolute right-4 top-4 text-[#58a7df]" size={18} /><h3 className="text-base font-black text-white">{resource.title}</h3><p className="mt-3 text-sm font-black text-[var(--color-text)]">{resource.type} - Uploaded by {author?.name}</p><p className="mt-3 text-sm font-black text-[var(--color-text)]">★ {resource.rating} - {formatNumber(resource.downloads)} Downloads - {formatNumber(resource.saves)} Saves</p></ResultShell>
}

function VideoResult({ video }) {
  const author = getUserById(video.authorId)
  return <ResultShell to={`/videos/${video.slug}`}><h3 className="text-base font-black text-white">{video.title}</h3><p className="mt-3 text-sm font-black text-[var(--color-text)]">Video - {video.duration} - by {author?.name}</p><p className="mt-3 text-sm font-black text-[var(--color-text)]">{formatNumber(video.views)} Views - {video.upvotes} Upvotes</p></ResultShell>
}

function QuestionResult({ question }) {
  return <ResultShell to={`/questions/${question.slug}`}><h3 className="text-base font-black text-white">{question.title}</h3><p className="mt-3 text-sm font-black text-[var(--color-text)]">Asked by {question.author?.name || 'StudyMate member'} - {question.upvotes ?? 0} Upvotes - {question.answerCount} Answers</p></ResultShell>
}

function UserResult({ user }) {
  return <ResultShell to={`/users/${user.username}`}><div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#260777] text-[var(--color-primary-light)]"><UserRound size={20} /></span><span><strong className="block text-white">{user.name}</strong><span className="text-sm font-black text-[var(--color-text)]">{user.points} Points</span></span></div></ResultShell>
}

export default SearchResults

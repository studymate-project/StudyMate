import { Bookmark, MessageCircle, Search, UserRound, Video as VideoIcon } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import Badge from '../components/common/Badge'
import Button from '../components/common/Button'
import SearchSection from '../components/search/SearchSection'
import Spinner from '../components/common/Spinner'
import { getApiErrorMessage } from '../api'
import { normalizeSearchQuery, searchContent, SEARCH_PAGE_SIZE } from '../api/search'
import { getSearchResultRoute } from '../utils/searchUtils'

const SEARCH_DEBOUNCE_MS = 350
const typeLabels = {
  resource: 'Resource',
  video: 'Video',
  question: 'Question',
  user: 'User',
}
const metadataLabels = {
  resource_type: 'Type',
  subject: 'Subject',
  topic: 'Topic',
  course: 'Course',
  semester: 'Semester',
  username: 'Username',
}

function isCanceledRequest(error) {
  return error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError'
}

function resultKey(result) {
  return `${result.type}:${result.id}`
}

function formatMetadataValue(value) {
  return String(value).replaceAll('_', ' ')
}

function ResultTypeIcon({ type }) {
  if (type === 'video') return <VideoIcon size={16} aria-hidden="true" />
  if (type === 'question') return <MessageCircle size={16} aria-hidden="true" />
  if (type === 'user') return <UserRound size={16} aria-hidden="true" />
  return <Bookmark size={16} aria-hidden="true" />
}

function SearchResultCard({ result }) {
  const route = getSearchResultRoute(result)
  const metadata = Object.entries(result.metadata || {})
    .filter(([key, value]) => key !== 'youtube_video_id' && value !== null && value !== undefined && value !== '')
    .slice(0, 4)

  const content = (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 text-xs font-black uppercase text-[var(--color-primary-light)]">
          <ResultTypeIcon type={result.type} />
          {typeLabels[result.type] || 'Result'}
        </span>
        {metadata.map(([key, value]) => (
          <Badge key={`${resultKey(result)}-${key}`} variant="blue">
            {metadataLabels[key] || key}: {formatMetadataValue(value)}
          </Badge>
        ))}
      </div>
      <h3 className="mt-3 text-base font-black text-white">{result.title}</h3>
      {result.snippet && <p className="mt-2 line-clamp-3 text-sm font-bold leading-6 text-[var(--color-text)]">{result.snippet}</p>}
      {typeof result.score === 'number' && (
        <p className="mt-3 text-xs font-black text-[var(--color-text-dim)]">Relevance {result.score.toFixed(3)}</p>
      )}
    </>
  )

  if (!route) {
    return <div className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5">{content}</div>
  }

  return <Link to={route} className="relative block border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 transition-colors hover:border-[var(--color-primary-light)]">{content}</Link>
}

function SearchResults() {
  const [searchParams, setSearchParams] = useSearchParams()
  const urlQuery = normalizeSearchQuery(searchParams.get('q'))
  const queryInput = useRef(null)
  const debounceTimer = useRef(null)

  const updateUrlQuery = useCallback((value, replace = true) => {
    const normalizedQuery = normalizeSearchQuery(value)
    setSearchParams(normalizedQuery ? { q: normalizedQuery } : {}, { replace })
  }, [setSearchParams])

  const submit = (event) => {
    event.preventDefault()
    if (debounceTimer.current) window.clearTimeout(debounceTimer.current)
    updateUrlQuery(queryInput.current?.value || '', false)
  }

  const handleQueryChange = (event) => {
    const nextQuery = event.target.value
    if (debounceTimer.current) window.clearTimeout(debounceTimer.current)
    debounceTimer.current = window.setTimeout(() => updateUrlQuery(nextQuery), SEARCH_DEBOUNCE_MS)
  }

  const clearSearch = () => {
    if (debounceTimer.current) window.clearTimeout(debounceTimer.current)
    if (queryInput.current) queryInput.current.value = ''
    updateUrlQuery('', false)
  }

  useEffect(() => {
    if (queryInput.current && queryInput.current.value !== urlQuery) queryInput.current.value = urlQuery
  }, [urlQuery])

  useEffect(() => () => {
    if (debounceTimer.current) window.clearTimeout(debounceTimer.current)
  }, [])

  return (
    <div>
      <section className="bg-[var(--color-band)] px-5 py-8 sm:px-8 lg:px-10">
        <div className="mx-auto max-w-[1260px]">
          <form onSubmit={submit} className="grid gap-3 md:grid-cols-[minmax(0,1fr)_110px_100px]">
            <label className="relative min-w-0">
              <span className="sr-only">Search resources, videos, questions, and users</span>
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-text)]" size={20} />
              <input
                ref={queryInput}
                type="search"
                defaultValue={urlQuery}
                onChange={handleQueryChange}
                placeholder="Search resources, videos, questions, and users"
                className="h-14 w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] pl-12 pr-4 text-base font-medium text-[var(--color-text)] outline-none focus:border-[var(--color-focus)]"
              />
            </label>
            <Button type="submit">Search</Button>
            <Button type="button" variant="secondary" onClick={clearSearch}>Clear</Button>
          </form>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {(urlQuery ? urlQuery.split(' ') : ['All']).map((chip) => <Badge key={chip} variant="blue">{chip}</Badge>)}
            <span className="text-sm font-black text-[var(--color-text)]">
              {urlQuery ? `Search results for "${urlQuery}"` : 'Search across resources, videos, and questions'}
            </span>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-[1260px]">
        <section className="min-w-0 px-5 py-7 sm:px-8">
          {!urlQuery && <div className="border-2 border-dashed border-[var(--color-border)] px-5 py-12 text-center text-sm font-black text-[var(--color-text)]">Enter a search term to find study resources, videos, questions, or users.</div>}
          {urlQuery && <SearchResultContent key={urlQuery} query={urlQuery} />}
        </section>
      </div>
    </div>
  )
}

function SearchResultContent({ query }) {
  const [results, setResults] = useState([])
  const [hasMore, setHasMore] = useState(false)
  const [nextOffset, setNextOffset] = useState(null)
  const [loading, setLoading] = useState(Boolean(query))
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState(null)
  const [retryNumber, setRetryNumber] = useState(0)
  const requestSequence = useRef(0)
  const loadMoreController = useRef(null)

  useEffect(() => {
    const sequence = requestSequence.current + 1
    requestSequence.current = sequence
    const controller = new AbortController()

    searchContent(query, { limit: SEARCH_PAGE_SIZE, offset: 0, signal: controller.signal })
      .then((data) => {
        if (sequence !== requestSequence.current) return
        setResults(data.results)
        setHasMore(data.hasMore)
        setNextOffset(data.nextOffset)
      })
      .catch((requestError) => {
        if (sequence !== requestSequence.current || isCanceledRequest(requestError)) return
        setError(requestError)
      })
      .finally(() => {
        if (sequence === requestSequence.current) setLoading(false)
      })

    return () => {
      controller.abort()
      loadMoreController.current?.abort()
    }
  }, [query, retryNumber])

  const loadMore = async () => {
    if (!hasMore || nextOffset === null || loading || loadingMore) return

    const sequence = requestSequence.current
    const controller = new AbortController()
    loadMoreController.current = controller
    setLoadingMore(true)

    try {
      const data = await searchContent(query, {
        limit: SEARCH_PAGE_SIZE,
        offset: nextOffset,
        signal: controller.signal,
      })
      if (sequence !== requestSequence.current) return

      setResults((currentResults) => {
        const existingKeys = new Set(currentResults.map(resultKey))
        return [...currentResults, ...data.results.filter((result) => !existingKeys.has(resultKey(result)))]
      })
      setHasMore(data.hasMore)
      setNextOffset(data.nextOffset)
    } catch (requestError) {
      if (sequence === requestSequence.current && !isCanceledRequest(requestError)) setError(requestError)
    } finally {
      if (sequence === requestSequence.current) {
        setLoadingMore(false)
        loadMoreController.current = null
      }
    }
  }

  if (loading) return <div className="flex items-center justify-center gap-3 px-5 py-12 text-sm font-black text-[var(--color-text)]" role="status"><Spinner label="Searching" /> Searching StudyMate</div>
  if (error) {
    return (
      <div className="border-2 border-[var(--color-danger)] bg-[var(--color-surface)] px-5 py-8 text-center" role="alert">
        <p className="text-sm font-black text-white">{getApiErrorMessage(error)}</p>
        <Button type="button" variant="secondary" className="mt-5" onClick={() => { setError(null); setLoading(true); setRetryNumber((value) => value + 1) }}>Try again</Button>
      </div>
    )
  }
  if (!results.length) return <div className="border-2 border-dashed border-[var(--color-border)] px-5 py-12 text-center text-sm font-black text-[var(--color-text)]">No resources, videos, questions, or users matched "{query}".</div>

  const sections = [
    { type: 'resource', title: 'Resources', viewAllTo: `/explore?search=${encodeURIComponent(query)}` },
    { type: 'video', title: 'Videos' },
    { type: 'question', title: 'Questions', viewAllTo: '/community' },
    { type: 'user', title: 'Users' },
  ]

  return (
    <>
      <p className="mb-6 text-sm font-black text-[var(--color-text)]" aria-live="polite">
        Showing {results.length}{hasMore ? '+' : ''} result{results.length === 1 ? '' : 's'}
      </p>
      {sections.map((section) => {
        const sectionResults = results.filter((result) => result.type === section.type)
        if (!sectionResults.length) return null
        return (
          <SearchSection
            key={section.type}
            title={section.title}
            showViewAll={Boolean(section.viewAllTo)}
            viewAllTo={section.viewAllTo}
          >
            {sectionResults.map((result) => <SearchResultCard key={resultKey(result)} result={result} />)}
          </SearchSection>
        )
      })}
      {hasMore && (
        <div className="flex justify-center pt-3">
          <Button type="button" variant="secondary" onClick={loadMore} disabled={loadingMore}>
            {loadingMore ? <><Spinner label="Loading more results" /> Loading more</> : 'Load more results'}
          </Button>
        </div>
      )}
    </>
  )
}

export default SearchResults

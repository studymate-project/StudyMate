import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../api'
import { deleteResourceRating, getResourceBySlug, saveResourceRating, trackResourceView } from '../api/resources'
import { useAuth } from '../auth/useAuth'
import RatingControl from '../components/common/RatingControl'
import DiscussionPanel from '../components/common/DiscussionPanel'
import Spinner from '../components/common/Spinner'
import PdfPreview from '../components/resources/PdfPreview'
import RelatedResourceList from '../components/resources/RelatedResourceList'
import ResourceHeader from '../components/resources/ResourceHeader'
import TagList from '../components/resources/TagList'
import UploaderCard from '../components/resources/UploaderCard'

const formatNumber = (value) => Number(value).toLocaleString('en-IN')

const initialState = {
  resource: null,
  loading: true,
  error: null,
  queryKey: null,
}

function ResourceMessage({ title, message, showBackLink = true, loadingLabel = '' }) {
  return (
    <div className="mx-auto flex w-full max-w-[900px] justify-center px-5 py-20 text-center sm:px-8">
      {loadingLabel ? <Spinner label={loadingLabel} /> : <div><h1 className="text-4xl font-black text-white">{title}</h1><p className="mt-4 font-bold text-[var(--color-text)]">{message}</p>{showBackLink ? <Link className="mt-7 inline-flex min-h-11 items-center rounded-xl border border-[var(--color-primary)] bg-[var(--color-primary)] px-5 font-black text-white" to="/explore">Back to Explore</Link> : null}</div>}
    </div>
  )
}

function SidebarLinkList({ title, items, pathPrefix }) {
  if (!items.length) return null

  return (
    <aside className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="text-base font-black text-white">{title}</h2>
      <div className="mt-4 h-px bg-[var(--color-border-strong)]" />
      <div className="mt-3 space-y-3">
        {items.map((item) => (
          <Link
            key={item.id}
            to={`/${pathPrefix}/${item.slug}`}
            className="block border-2 border-[var(--color-border)] p-3 text-sm font-black leading-snug text-white transition-colors hover:border-[var(--color-primary-light)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
          >
            {item.shortTitle || item.title}
          </Link>
        ))}
      </div>
    </aside>
  )
}

function ExpandableDescription({ heading, description, stats = [] }) {
  const [expanded, setExpanded] = useState(false)
  const text = typeof description === 'string' ? description.trim() : ''

  return (
    <div className="mt-6">
      <h2 className="text-base font-black text-white">{heading}</h2>
      <p className={`mt-3 min-h-[2.75rem] text-base font-black leading-relaxed text-white/90 ${text && !expanded ? 'line-clamp-2' : ''}`}>
        {text || 'No description available.'}
      </p>
      {text ? (
        <button
          type="button"
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
          className="mt-2 text-sm font-black text-[var(--color-primary-light)] underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
        >
          {expanded ? 'Less' : 'More'}
        </button>
      ) : null}
      {stats.length ? (
        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm font-black text-[var(--color-text)]" aria-label="Resource statistics">
          {stats.map((stat, index) => (
            <span key={stat.label} className="inline-flex items-center gap-3">
              {index ? <span aria-hidden="true">·</span> : null}
              <span>{stat.label}: {stat.value}</span>
            </span>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function ResourceDetails() {
  const { slug } = useParams()
  return <ResourceDetailsView key={slug} slug={slug} />
}

function ResourceDetailsView({ slug }) {
  const queryKey = slug || ''
  const { status: authStatus } = useAuth()
  const [state, setState] = useState(initialState)
  const [downloadCount, setDownloadCount] = useState(null)
  const [userRating, setUserRating] = useState(null)
  const [ratingState, setRatingState] = useState('idle')
  const [ratingError, setRatingError] = useState('')
  const [ratingNotice, setRatingNotice] = useState('')
  const trackedViewId = useRef(null)

  useEffect(() => {
    let isCurrent = true

    getResourceBySlug(queryKey).then(
      (resource) => {
        if (!isCurrent) return

        setState({ resource, loading: false, error: null, queryKey })
        setUserRating(resource.userRating ?? null)
        if (resource.id && trackedViewId.current !== resource.id) {
          trackedViewId.current = resource.id
          trackResourceView(resource.id).catch(() => {
            // View tracking is best effort and must not block the resource.
          })
        }
      },
      (error) => {
        if (isCurrent) setState({ resource: null, loading: false, error, queryKey })
      },
    )

    return () => {
      isCurrent = false
    }
  }, [queryKey])

  const isCurrentQuery = state.queryKey === queryKey
  const loading = !isCurrentQuery || state.loading
  const resource = isCurrentQuery ? state.resource : null
  const error = isCurrentQuery ? state.error : null

  const handleRatingChange = async (nextRating) => {
    if (authStatus !== 'authenticated') {
      setRatingNotice('Please sign in to submit a rating.')
      return
    }

    setRatingState('loading')
    setRatingError('')
    setRatingNotice('')
    try {
      await saveResourceRating(resource.id, nextRating)
      const refreshedResource = await getResourceBySlug(queryKey)
      setState({ resource: refreshedResource, loading: false, error: null, queryKey })
      setUserRating(nextRating)
      setRatingNotice('Your rating was saved.')
    } catch (requestError) {
      setRatingError(getApiErrorMessage(requestError))
    } finally {
      setRatingState('idle')
    }
  }

  const handleRatingDelete = async () => {
    if (authStatus !== 'authenticated') {
      setRatingNotice('Please sign in to manage your rating.')
      return
    }

    setRatingState('loading')
    setRatingError('')
    setRatingNotice('')
    try {
      await deleteResourceRating(resource.id)
      const refreshedResource = await getResourceBySlug(queryKey)
      setState({ resource: refreshedResource, loading: false, error: null, queryKey })
      setUserRating(null)
      setRatingNotice('Your rating was removed.')
    } catch (requestError) {
      setRatingError(getApiErrorMessage(requestError))
    } finally {
      setRatingState('idle')
    }
  }

  if (loading) return <ResourceMessage loadingLabel="Loading resource" showBackLink={false} />
  if (error?.status === 404) return <ResourceMessage title="Resource Not Found" message="This resource may have been moved or removed." />
  if (error) return <ResourceMessage title="Unable to Load Resource" message={getApiErrorMessage(error)} />
  if (!resource) return <ResourceMessage title="Resource Not Found" message="This resource may have been moved or removed." />

  const stats = [
    { value: resource.views, label: 'Views' },
    { value: downloadCount ?? resource.downloads, label: 'Downloads' },
    { value: resource.saves, label: 'Saves' },
    { value: resource.upvotes, label: 'Upvotes' },
  ]
    .filter((stat) => stat.value != null)
    .map((stat) => ({ ...stat, value: formatNumber(stat.value) }))

  return (
    <div className="mx-auto w-full max-w-[1260px] px-5 py-6 sm:px-8 lg:px-10">
      <nav className="flex flex-wrap gap-2 text-sm font-black text-[var(--color-text)]" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <span>/</span>
        <Link to={`/explore?subject=${encodeURIComponent(resource.subject.toLowerCase())}`}>{resource.subject}</Link>
        <span>/</span>
        <span>{resource.topic}</span>
        <span>/</span>
        <span className="text-[var(--color-primary-light)]">{resource.title}</span>
      </nav>

      <div className="mt-5 grid gap-9 lg:grid-cols-[minmax(0,1fr)_330px]">
        <div className="min-w-0 space-y-6">
          <ResourceHeader
            resource={resource}
            author={resource.author}
            onDownloadCountChange={setDownloadCount}
            descriptionContent={<ExpandableDescription heading="Description" description={resource.description} stats={stats} />}
          />
          <RatingControl
            key={`resource-rating-${resource.id}-${userRating ?? 'none'}`}
            itemLabel="resource"
            value={userRating}
            authStatus={authStatus}
            isSaving={ratingState === 'loading'}
            error={ratingError}
            notice={ratingNotice}
            onSubmit={handleRatingChange}
            onDelete={handleRatingDelete}
          />
          <PdfPreview resourceSlug={resource.slug} resourceUrl={resource.resourceUrl} resourceType={resource.resourceType} />
          <TagList tags={resource.tags} />
          <DiscussionPanel itemLabel="this resource" targetType="resource" targetId={resource.id} authStatus={authStatus} />
        </div>
        <div className="space-y-6">
          <UploaderCard user={resource.author} />
          <RelatedResourceList resources={[]} />
          <SidebarLinkList title="Related Questions" items={[]} pathPrefix="questions" />
          <SidebarLinkList title="Related Videos" items={[]} pathPrefix="videos" />
        </div>
      </div>
    </div>
  )
}

export default ResourceDetails

import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../api'
import { getResourceBySlug, trackResourceView } from '../api/resources'
import PdfPreview from '../components/resources/PdfPreview'
import RelatedResourceList from '../components/resources/RelatedResourceList'
import ResourceHeader from '../components/resources/ResourceHeader'
import ResourceStats from '../components/resources/ResourceStats'
import TagList from '../components/resources/TagList'
import UploaderCard from '../components/resources/UploaderCard'

const formatNumber = (value) => Number(value).toLocaleString('en-IN')

const initialState = {
  resource: null,
  loading: true,
  error: null,
  queryKey: null,
}

function ResourceMessage({ title, message, showBackLink = true }) {
  return (
    <div className="mx-auto w-full max-w-[900px] px-5 py-20 text-center sm:px-8">
      <h1 className="text-4xl font-black text-white">{title}</h1>
      <p className="mt-4 font-bold text-[var(--color-text)]">{message}</p>
      {showBackLink ? <Link className="mt-7 inline-flex min-h-11 items-center border border-[var(--color-primary)] bg-[var(--color-primary)] px-5 font-black text-white" to="/explore">Back to Explore</Link> : null}
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

function ResourceDetails() {
  const { slug } = useParams()
  return <ResourceDetailsView key={slug} slug={slug} />
}

function ResourceDetailsView({ slug }) {
  const queryKey = slug || ''
  const [state, setState] = useState(initialState)
  const [downloadCount, setDownloadCount] = useState(null)
  const trackedViewId = useRef(null)

  useEffect(() => {
    let isCurrent = true

    getResourceBySlug(queryKey).then(
      (resource) => {
        if (!isCurrent) return

        setState({ resource, loading: false, error: null, queryKey })
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

  if (loading) return <ResourceMessage title="Loading Resource" message="Fetching the latest resource details..." showBackLink={false} />
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
          <ResourceHeader resource={resource} author={resource.author} onDownloadCountChange={setDownloadCount} />
          <ResourceStats stats={stats} />
          <PdfPreview resourceSlug={resource.slug} resourceUrl={resource.resourceUrl} resourceType={resource.resourceType} />
          <TagList tags={resource.tags} />
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

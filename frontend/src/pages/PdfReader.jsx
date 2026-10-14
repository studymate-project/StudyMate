import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../api'
import { getResourceBySlug } from '../api/resources'
import Button from '../components/common/Button'
import Spinner from '../components/common/Spinner'
import PdfDocumentViewer from '../components/resources/PdfDocumentViewer'

const initialState = { resource: null, loading: true, error: null, queryKey: null }

function ReaderMessage({ title, message, showBackLink = true, loadingLabel = '' }) {
  return (
    <div className="mx-auto flex max-w-[900px] justify-center px-5 py-20 text-center">
      {loadingLabel ? <Spinner label={loadingLabel} /> : <div><h1 className="text-4xl font-black text-white">{title}</h1><p className="mt-4 font-bold text-[var(--color-text)]">{message}</p>{showBackLink ? <Button to="/explore" className="mt-7">Back to Explore</Button> : null}</div>}
    </div>
  )
}

function PdfReader() {
  const { slug } = useParams()
  const queryKey = slug || ''
  const [state, setState] = useState(initialState)
  const [mediaState, setMediaState] = useState({ url: null, status: 'idle' })

  useEffect(() => {
    let isCurrent = true

    getResourceBySlug(queryKey).then(
      (resource) => {
        if (isCurrent) setState({ resource, loading: false, error: null, queryKey })
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
  const resource = isCurrentQuery ? state.resource : null
  const error = isCurrentQuery ? state.error : null
  const resourceUrl = resource?.resourceUrl || null
  const markMediaReady = useCallback(() => {
    if (resourceUrl) setMediaState({ url: resourceUrl, status: 'ready' })
  }, [resourceUrl])
  const markMediaError = useCallback(() => {
    if (resourceUrl) setMediaState({ url: resourceUrl, status: 'error' })
  }, [resourceUrl])

  if (!isCurrentQuery || state.loading) return <ReaderMessage loadingLabel="Loading resource" showBackLink={false} />
  if (error?.status === 404) return <ReaderMessage title="Resource Not Found" message="This resource may have been moved or removed." />
  if (error) return <ReaderMessage title="Unable to Load Resource" message={getApiErrorMessage(error)} />
  if (!resource) return <ReaderMessage title="Resource Not Found" message="This resource may have been moved or removed." />

  const extension = getFileExtension(resource.resourceUrl)
  const isPdf = resource.resourceType === 'pdf' || resource.type?.toLowerCase() === 'pdf' || extension === 'pdf'
  const isLink = resource.resourceType === 'link'
  const currentMediaState = mediaState.url === resource.resourceUrl ? mediaState.status : 'loading'
  const showMediaError = currentMediaState === 'error'

  return (
    <div className="mx-auto w-full max-w-[1100px] px-5 py-8 sm:px-8">
      <Link to={`/resources/${resource.slug}`} className="text-sm font-black text-[var(--color-primary-light)]">Back to resource</Link>
      <h1 className="mt-4 text-3xl font-black text-white">{resource.title}</h1>
      <div className="mt-6 min-h-[640px] border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5">
        {!resource.resourceUrl
          ? <ReaderNotice message="Media is not available for this resource." />
          : isPdf
            ? showMediaError
              ? <ReaderNotice message="This PDF could not be displayed in the browser." action={<MediaFallbackLink url={resource.resourceUrl} /> } />
              : <PdfDocumentViewer url={resource.resourceUrl} onReady={markMediaReady} onError={markMediaError} />
            : isLink
              ? <ReaderNotice message="This is an external resource link." action={<a href={resource.resourceUrl} target="_blank" rel="noreferrer" className="mt-5 inline-flex min-h-11 items-center rounded-xl border border-[var(--color-primary)] bg-[var(--color-primary)] px-5 font-black text-white">Open external link</a>} />
              : <ReaderNotice message="This file type cannot be previewed inside the browser. Return to the resource page to use Download." action={<MediaFallbackLink url={resource.resourceUrl} />} />}
      </div>
    </div>
  )
}

function MediaFallbackLink({ url }) {
  return <a href={url} target="_blank" rel="noreferrer" className="mt-5 inline-flex min-h-11 items-center rounded-xl border border-[var(--color-primary)] bg-[var(--color-primary)] px-5 font-black text-white">Open or download file</a>
}

function getFileExtension(value) {
  if (!value) return ''
  try {
    const parsedUrl = new URL(value, window.location.origin)
    const queryPublicId = parsedUrl.searchParams.get('public_id')
    const queryExtension = queryPublicId?.split('.').pop()?.toLowerCase()
    if (queryExtension && queryExtension !== queryPublicId) return queryExtension
    const pathname = parsedUrl.pathname
    return pathname.split('.').pop()?.toLowerCase() || ''
  } catch {
    return value.split('?')[0].split('.').pop()?.toLowerCase() || ''
  }
}

function ReaderNotice({ message, action = null }) {
  return <div className="flex min-h-[590px] flex-col items-center justify-center text-center"><p className="max-w-xl font-bold text-[var(--color-text)]">{message}</p>{action}</div>
}

export default PdfReader

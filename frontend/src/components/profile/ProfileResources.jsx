import { ExternalLink, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getApiErrorMessage } from '../../api/errors'
import { confirmProfileResourceDeletion, profileResourceOpenTarget } from './profileResourceActions'

function ProfileResources({ resources = [], title = 'Resources', empty = 'No resources shared yet.', onDelete = null, onUnsave = null }) {
  const [busyKey, setBusyKey] = useState(null)
  const [error, setError] = useState('')

  const actionKey = (resource) => `${resource.targetType || 'resource'}-${resource.id}`
  const handleDelete = async (resource) => {
    if (!onDelete || busyKey) return
    if (!confirmProfileResourceDeletion(resource, window.confirm)) return

    const key = actionKey(resource)
    setBusyKey(key)
    setError('')
    try {
      await onDelete(resource)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setBusyKey(null)
    }
  }

  const handleUnsave = async (resource) => {
    if (!onUnsave || busyKey) return
    const key = actionKey(resource)
    setBusyKey(key)
    setError('')
    try {
      await onUnsave(resource)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setBusyKey(null)
    }
  }

  return <section aria-label={title}><h2 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text)]">{title}</h2>{error ? <p className="mt-3 border border-[var(--color-danger)] p-3 text-sm text-[var(--color-danger)]" role="alert">{error}</p> : null}{!resources.length ? <p className="mt-3 border-2 border-[var(--color-border)] p-5 text-sm text-[var(--color-text)]">{empty}</p> : <div className="mt-3 space-y-3">{resources.map((resource) => {
    const key = actionKey(resource)
    const openUrl = profileResourceOpenTarget(resource)
    const isExternal = resource.resourceType === 'link' && resource.resourceUrl
    return <article key={key} className="flex flex-col gap-4 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><h3 className="break-words text-sm font-semibold text-white">{resource.title}</h3><div className="mt-2 flex flex-wrap gap-2"><span className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2 py-0.5 text-xs text-[var(--color-text)]">{resource.subject || 'General'}</span><span className="rounded-lg border border-[var(--color-border-strong)] px-2 py-0.5 text-xs text-[var(--color-text)]">{resource.type || 'Resource'}</span>{resource.uploadedAt ? <span className="px-2 py-0.5 text-xs text-[var(--color-text-dim)]">{resource.uploadedAt}</span> : null}</div>{resource.description ? <p className="mt-2 line-clamp-2 text-sm text-[var(--color-text)]">{resource.description}</p> : null}</div><div className="flex shrink-0 flex-wrap gap-2 sm:justify-end">{isExternal ? <a href={openUrl} target="_blank" rel="noreferrer" className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 text-sm font-semibold text-[var(--color-text)] hover:bg-[var(--color-blue-hover)]">Open <ExternalLink size={15} /></a> : <Link to={openUrl} className="inline-flex min-h-9 items-center justify-center rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-4 text-sm font-semibold text-[var(--color-text)] hover:bg-[var(--color-blue-hover)]">View</Link>}{onDelete ? <button type="button" onClick={() => handleDelete(resource)} disabled={busyKey !== null} aria-label={`Delete ${resource.title}`} className="inline-flex min-h-9 min-w-9 items-center justify-center rounded-lg border border-[var(--color-border)] text-[var(--color-text)] hover:border-[var(--color-danger)] hover:text-[var(--color-danger)] disabled:cursor-not-allowed disabled:opacity-50"><Trash2 size={17} /></button> : null}{onUnsave ? <button type="button" onClick={() => handleUnsave(resource)} disabled={busyKey !== null} aria-label={`Remove ${resource.title} from saved resources`} className="inline-flex min-h-9 items-center justify-center rounded-lg border border-[var(--color-border)] px-3 text-sm text-[var(--color-text)] hover:text-white disabled:cursor-not-allowed disabled:opacity-50">{busyKey === key ? 'Removing…' : 'Unsave'}</button> : null}</div></article>
  })}</div>}</section>
}

export default ProfileResources

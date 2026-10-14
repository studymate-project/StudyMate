import { BookOpen, Download, FileText, Save, Share2 } from 'lucide-react'
import { useRef, useState } from 'react'
import { saveResource, unsaveResource } from '../../api/resources'
import { getApiErrorMessage } from '../../api'
import { trackResourceDownload } from '../../api/resources'
import Badge from '../common/Badge'
import Button from '../common/Button'
import IconButton from '../common/IconButton'
import Rating from '../common/Rating'

function ResourceHeader({ resource, author, onDownloadCountChange, descriptionContent }) {
  const [downloadState, setDownloadState] = useState('idle')
  const [saveState, setSaveState] = useState('idle')
  const [saved, setSaved] = useState(resource.isSaved)
  const [actionError, setActionError] = useState('')
  const downloadInFlight = useRef(false)
  const isLink = resource.resourceType === 'link'

  const handleDownload = () => {
    if (!resource.resourceUrl || isLink || downloadInFlight.current) return

    downloadInFlight.current = true
    setDownloadState('loading')
    setActionError('')
    try {
      const anchor = document.createElement('a')
      anchor.href = resource.resourceUrl
      anchor.download = resource.title || 'studymate-resource'
      anchor.rel = 'noopener'
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
    } catch (error) {
      setActionError(getApiErrorMessage(error))
      downloadInFlight.current = false
      setDownloadState('idle')
      return
    }

    trackResourceDownload(resource.id)
      .then((result) => onDownloadCountChange?.(result.downloads))
      .catch((error) => {
        setActionError(getApiErrorMessage(error))
      })
      .finally(() => {
        downloadInFlight.current = false
        setDownloadState('idle')
      })
  }

  const handleSave = async () => {
    if (saveState === 'loading') return

    setSaveState('loading')
    setActionError('')
    try {
      if (saved) {
        await unsaveResource(resource.id)
        setSaved(false)
      } else {
        await saveResource(resource.id)
        setSaved(true)
      }
    } catch (error) {
      setActionError(getApiErrorMessage(error))
    } finally {
      setSaveState('idle')
    }
  }

  return (
    <section className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 sm:p-7">
      <div className="grid gap-5 sm:grid-cols-[78px_minmax(0,1fr)]">
        <div className="flex h-[78px] w-[78px] items-center justify-center rounded-lg bg-[var(--color-surface-muted)] text-[var(--color-primary-light)]">
          <FileText size={36} />
        </div>
        <div className="min-w-0">
          <h1 className="break-words text-3xl font-black leading-tight text-white sm:text-4xl">{resource.title}</h1>
          <div className="mt-3 flex flex-wrap gap-2">
            {[resource.type, resource.topic, resource.subject, resource.course, resource.semester].filter(Boolean).map((badge, index) => (
              <Badge key={badge} variant={index === 0 ? 'blue' : index === 1 ? 'purple' : 'teal'}>
                {badge}
              </Badge>
            ))}
          </div>
          <p className="mt-3 text-sm font-black text-[var(--color-text)]">
            Uploaded by {author?.name || 'StudyMate member'}{resource.uploadedAt ? ` - ${resource.uploadedAt}` : ''}
          </p>
          <Rating value={resource.rating} count={resource.ratingCount} size={22} className="mt-3" />
        </div>
      </div>

      {descriptionContent || <p className="mt-6 max-w-4xl text-base font-black leading-snug text-white/90">{resource.description}</p>}

      <div className="mt-6 flex flex-wrap gap-3">
        <Button to={`/resources/${resource.slug}/read`}>
          <BookOpen size={18} />
          Read
        </Button>
        <Button variant="secondary" onClick={handleDownload} disabled={!resource.resourceUrl || isLink || downloadState === 'loading'}>
          <Download size={18} />
          {downloadState === 'loading' ? 'Downloading...' : 'Download'}
        </Button>
        <div className="flex items-center gap-1" aria-label="Resource actions">
          <IconButton
            label={saved ? 'Remove resource from saved items' : 'Save resource'}
            variant="default"
            onClick={handleSave}
            disabled={saveState === 'loading'}
            aria-pressed={saved}
            className={`h-11 w-11 rounded-full border-0 bg-transparent p-0 hover:border-transparent hover:bg-transparent ${saved ? 'text-[var(--color-primary-light)]' : ''}`}
          >
            <Save size={20} className={saved ? 'fill-current' : ''} aria-hidden="true" />
          </IconButton>
          <IconButton
            label="Share resource"
            variant="default"
            className="h-11 w-11 rounded-full border-0 bg-transparent p-0 hover:border-transparent hover:bg-transparent"
          >
            <Share2 size={20} aria-hidden="true" />
          </IconButton>
        </div>
      </div>
      {actionError ? <p role="alert" className="mt-3 text-sm font-bold text-[var(--color-danger)]">{actionError}</p> : null}
    </section>
  )
}

export default ResourceHeader

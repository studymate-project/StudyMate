import { BookOpen, Download, ExternalLink, FileText, Save, Share2 } from 'lucide-react'
import { useRef, useState } from 'react'
import { saveResource, unsaveResource } from '../../api/resources'
import { getApiErrorMessage } from '../../api'
import { trackResourceDownload } from '../../api/resources'
import Badge from '../common/Badge'
import Button from '../common/Button'
import Rating from '../common/Rating'

function ResourceHeader({ resource, author, onDownloadCountChange }) {
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
        <div className="flex h-[78px] w-[78px] items-center justify-center bg-[#073c68] text-[var(--color-primary-light)]">
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
          {resource.rating != null ? <Rating value={resource.rating} showValue={false} className="mt-3" /> : null}
        </div>
      </div>

      <p className="mt-6 max-w-4xl text-base font-black leading-snug text-white/90">{resource.description}</p>

      <div className="mt-6 flex flex-wrap gap-3">
        <Button to={`/resources/${resource.slug}/read`}>
          <BookOpen size={18} />
          Read
        </Button>
        <Button className="border-[#009a8d] bg-[#009a8d] hover:bg-[#00b2a3]" onClick={handleDownload} disabled={!resource.resourceUrl || isLink || downloadState === 'loading'}>
          <Download size={18} />
          {downloadState === 'loading' ? 'Downloading...' : 'Download'}
        </Button>
        <Button variant="secondary" className="border-[#58a7df] text-[#58a7df]" onClick={handleSave} disabled={saveState === 'loading'}>
          <Save size={18} />
          {saveState === 'loading' ? 'Saving...' : saved ? 'Saved' : 'Save'}
        </Button>
        <Button variant="dark">
          <ExternalLink size={18} />
          <Share2 size={18} className="sr-only" />
          Share
        </Button>
      </div>
      {actionError ? <p role="alert" className="mt-3 text-sm font-bold text-[#ffadb6]">{actionError}</p> : null}
    </section>
  )
}

export default ResourceHeader

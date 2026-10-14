import { Link2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { createResource, createVideo, getApiErrorMessage, getApiFieldErrors } from '../api'
import Button from '../components/common/Button'
import Toast from '../components/common/Toast'
import FileDropzone from '../components/upload/FileDropzone'
import ResourceTypeSelector from '../components/upload/ResourceTypeSelector'
import UploadGuidelines from '../components/upload/UploadGuidelines'
import VideoUploadField from '../components/video/VideoUploadField'
import Footer from '../components/layout/Footer'
import { parseYouTubeUrl } from '../utils/youtubeUtils'

const initialForm = {
  title: '',
  description: '',
  subject: '',
  topic: '',
  course: '',
  semester: '',
  selectedType: 'File',
  youtubeUrl: '',
  externalUrl: '',
}
const requiredFields = ['title', 'description', 'subject', 'topic', 'course', 'semester']
const draftKey = 'studymate-upload-draft'
const resourceTypeMap = { File: 'file', Link: 'link' }

function createUploadId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID()
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function loadDraft() {
  try {
    const draft = JSON.parse(localStorage.getItem(draftKey) || '{}')
    const selectedType = ['File', 'Video', 'Link'].includes(draft.selectedType) ? draft.selectedType : initialForm.selectedType
    return { ...initialForm, ...draft, selectedType }
  } catch {
    return initialForm
  }
}

function UploadResource() {
  const [form, setForm] = useState(loadDraft)
  const [file, setFile] = useState(null)
  const [errors, setErrors] = useState({})
  const [fileError, setFileError] = useState('')
  const [videoError, setVideoError] = useState('')
  const [toast, setToast] = useState(null)
  const [uploadState, setUploadState] = useState('idle')
  const [uploadMessage, setUploadMessage] = useState('')
  const [createdResource, setCreatedResource] = useState(null)
  const [uploadId, setUploadId] = useState(createUploadId)
  const isVideo = form.selectedType === 'Video'
  const isLink = form.selectedType === 'Link'

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: '' }))
  }

  const setSelectedType = (selectedType) => {
    updateField('selectedType', selectedType)
    setFileError('')
    setVideoError('')
    setUploadState('idle')
    setUploadMessage('')
  }

  const validate = () => {
    const nextErrors = requiredFields.reduce(
      (all, field) => (!form[field].trim() ? { ...all, [field]: 'This field is required.' } : all),
      {},
    )
    const video = isVideo ? parseYouTubeUrl(form.youtubeUrl) : null
    const validLink = /^https?:\/\//i.test(form.externalUrl.trim())
    setVideoError(isVideo && !video ? 'Please enter a valid YouTube video URL.' : '')
    setFileError(!isVideo && !isLink && !file ? 'Please choose a resource file.' : '')
    if (isLink && !validLink) nextErrors.externalUrl = 'Enter a valid http(s) link.'
    setErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
      && (isVideo ? Boolean(video) : isLink ? validLink : Boolean(file))
  }

  const resetAfterSuccess = () => {
    setForm(initialForm)
    setFile(null)
    setErrors({})
    setFileError('')
    setVideoError('')
    localStorage.removeItem(draftKey)
    setUploadId(createUploadId())
  }

  const submit = async (event) => {
    event.preventDefault()
    if (uploadState === 'uploading') return
    setCreatedResource(null)
    if (!validate()) {
      setUploadState('validation')
      setUploadMessage('Please correct the highlighted fields.')
      return
    }

    if (isVideo) {
      setUploadState('uploading')
      setUploadMessage('Publishing video...')
      try {
        const video = await createVideo({
          title: form.title.trim(),
          description: form.description.trim(),
          subject: form.subject.trim(),
          topic: form.topic.trim(),
          course: form.course.trim(),
          semester: form.semester.trim(),
          youtube_url: form.youtubeUrl.trim(),
        })
        setCreatedResource({ ...video, kind: 'video' })
        setUploadState('success')
        setUploadMessage('Video resource published successfully.')
        setToast({ message: 'Video resource published successfully.', type: 'success' })
        resetAfterSuccess()
      } catch (error) {
        const fieldErrors = getApiFieldErrors(error)
        setErrors((current) => ({ ...current, ...fieldErrors }))
        const message = getApiErrorMessage(error)
        setUploadState(error?.status === 400 ? 'validation' : 'api')
        setUploadMessage(message)
        setToast({ message, type: 'error' })
      }
      return
    }

    const formData = new FormData()
    formData.append('title', form.title.trim())
    formData.append('description', form.description.trim())
    formData.append('subject', form.subject.trim())
    formData.append('topic', form.topic.trim())
    formData.append('course', form.course.trim())
    formData.append('semester', form.semester.trim())
    formData.append('resource_type', resourceTypeMap[form.selectedType])
    if (isLink) formData.append('external_url', form.externalUrl.trim())
    if (!isLink) formData.append('file', file)

    setUploadState('uploading')
    setUploadMessage(isLink ? 'Publishing link...' : 'Uploading resource...')
    try {
      const resource = await createResource(formData, uploadId)
      setCreatedResource({ ...resource, kind: 'resource' })
      setUploadState('success')
      setUploadMessage('Resource published successfully. It is ready to be discovered.')
      setToast({ message: 'Resource published successfully.', type: 'success' })
      resetAfterSuccess()
    } catch (error) {
      const fieldErrors = getApiFieldErrors(error)
      const visibleFieldErrors = Object.fromEntries(Object.entries(fieldErrors).filter(([field]) => field !== 'file'))
      setErrors((current) => ({ ...current, ...visibleFieldErrors }))
      if (fieldErrors.file) setFileError(fieldErrors.file)
      const message = getApiErrorMessage(error)
      setUploadState(error?.status === 400 ? 'validation' : 'api')
      setUploadMessage(message)
      setToast({ message, type: 'error' })
    }
  }

  const saveDraft = () => {
    localStorage.setItem(draftKey, JSON.stringify(form))
    setToast({ message: 'Draft saved on this device.', type: 'success' })
  }

  const createdPath = createdResource?.slug
    ? createdResource.kind === 'video' ? `/videos/${createdResource.slug}` : `/resources/${createdResource.slug}`
    : null

  return <>
    <section className="bg-[var(--color-hero)]"><div className="mx-auto w-full max-w-[1260px] px-5 py-6 sm:px-8 lg:px-10"><h1 className="text-2xl font-bold text-white sm:text-3xl">Share a Resource</h1><p className="mt-1 text-sm font-medium text-[var(--color-text-dim)]">Help other students by sharing your notes, guides, and materials.</p></div></section>
    <main className="mx-auto w-full max-w-[1260px] px-5 py-7 sm:px-8 lg:px-10">
      <form onSubmit={submit} noValidate className="grid gap-7 lg:grid-cols-[minmax(0,1fr)_310px] lg:items-start">
        <section className="min-w-0 space-y-5">
          <Field label="Resource title" error={errors.title}><input value={form.title} onChange={(event) => updateField('title', event.target.value)} placeholder="DBMS Normalization Short Notes" className="control" /></Field>
          <Field label="Description" error={errors.description}><textarea value={form.description} onChange={(event) => updateField('description', event.target.value)} placeholder="Describe what other students will learn from this resource." className="control min-h-28 resize-y" /></Field>
          <div className="grid gap-5 sm:grid-cols-2">
            <TextField label="Subject" value={form.subject} onChange={(value) => updateField('subject', value)} placeholder="DBMS, Java, DSA..." error={errors.subject} />
            <TextField label="Topic" value={form.topic} onChange={(value) => updateField('topic', value)} placeholder="Normalization, OOP..." error={errors.topic} />
            <TextField label="Course" value={form.course} onChange={(value) => updateField('course', value)} placeholder="B.Tech Computer Science" error={errors.course} />
            <TextField label="Semester" value={form.semester} onChange={(value) => updateField('semester', value)} placeholder="5th Semester" error={errors.semester} />
          </div>
          <Field label="Resource type" error={errors.selectedType}><ResourceTypeSelector value={form.selectedType} onChange={setSelectedType} /></Field>
        </section>
        <aside className="space-y-4">
          {isVideo ? <VideoUploadField value={form.youtubeUrl} onChange={(value) => { updateField('youtubeUrl', value); setVideoError('') }} error={videoError} /> : isLink ? <LinkResourceField value={form.externalUrl} onChange={(value) => updateField('externalUrl', value)} error={errors.externalUrl} /> : <FileDropzone file={file} error={fileError} onFileChange={(nextFile, nextError) => { setFile(nextFile); setFileError(nextError); setUploadState(nextError ? 'validation' : 'idle'); setUploadMessage(nextError || '') }} />}
          <UploadGuidelines />
          {uploadMessage ? <p role={uploadState === 'uploading' || uploadState === 'success' ? 'status' : 'alert'} className={`px-2 text-center text-sm font-semibold ${uploadState === 'success' || uploadState === 'uploading' ? 'text-[var(--color-text)]' : 'text-[var(--color-danger)]'}`}>{uploadMessage}{createdPath ? <>{' '}<Link to={createdPath} className="underline">View resource</Link></> : null}</p> : null}
          <Button type="submit" className="w-full" disabled={uploadState === 'uploading'}>{uploadState === 'uploading' ? 'Publishing...' : 'Publish Resource'}</Button>
          <Button type="button" variant="secondary" className="w-full" onClick={saveDraft}>Save as Draft</Button>
          <p className="px-2 text-center text-xs font-medium leading-relaxed text-[var(--color-text-dim)]">Add clear details so other students can find your resource faster.</p>
        </aside>
      </form>
    </main>
    <Footer />
    {toast ? <Toast {...toast} onDismiss={() => setToast(null)} /> : null}
  </>
}

function LinkResourceField({ value, onChange, error }) {
  return <section className="space-y-3 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5"><Link2 className="text-[var(--color-text)]" size={27} /><label className="block"><span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-[var(--color-text)]">Resource link</span><input type="url" value={value} onChange={(event) => onChange(event.target.value)} placeholder="https://example.com/study-resource" className="control" />{error ? <span className="mt-2 block text-sm font-medium text-[var(--color-danger)]">{error}</span> : null}</label><p className="text-sm leading-relaxed text-[var(--color-text)]">Add a publicly accessible study resource link.</p></section>
}

function Field({ label, error, children }) { return <label className="block"><span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-[var(--color-text)]">{label}</span>{children}{error ? <span className="mt-1 block text-sm font-medium text-[var(--color-danger)]">{error}</span> : null}</label> }
function TextField({ label, value, onChange, placeholder, error }) { return <Field label={label} error={error}><input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="control" /></Field> }

export default UploadResource

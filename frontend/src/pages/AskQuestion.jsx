import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createQuestion, getApiErrorMessage, getApiFieldErrors } from '../api'
import Button from '../components/common/Button'
import Toast from '../components/common/Toast'

function AskQuestion() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ title: '', body: '', tags: '', subject: 'Java', topic: 'OOP' })
  const [errors, setErrors] = useState({})
  const [posting, setPosting] = useState(false)
  const [toast, setToast] = useState(null)
  const [createdQuestion, setCreatedQuestion] = useState(null)

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: '' }))
  }

  const submit = async (event) => {
    event.preventDefault()
    if (posting) return
    setPosting(true)
    setErrors({})
    try {
      const question = await createQuestion({ ...form, title: form.title.trim(), body: form.body.trim(), tag_names: form.tags })
      setCreatedQuestion(question)
      setToast({ message: 'Question posted successfully.', type: 'success' })
      setForm({ title: '', body: '', tags: '', subject: 'Java', topic: 'OOP' })
    } catch (error) {
      setErrors(getApiFieldErrors(error))
      setToast({ message: getApiErrorMessage(error), type: 'error' })
    } finally {
      setPosting(false)
    }
  }

  return (
    <>
      <div className="mx-auto w-full max-w-[900px] px-5 py-8 sm:px-8">
      <h1 className="text-4xl font-black text-white">Ask a Question</h1>
      <p className="mt-3 font-black text-[var(--color-text)]">Share the exact point where you are stuck so other students can help.</p>

      <form
        className="mt-7 space-y-5 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5"
        onSubmit={submit}
      >
        <Field label="Question Title" value={form.title} error={errors.title} onChange={(value) => updateField('title', value)} placeholder="What is the difference between..." />
        <label className="block">
          <span className="font-black text-white">Description</span>
          <textarea required value={form.body} onChange={(event) => updateField('body', event.target.value)} className="mt-2 min-h-36 w-full border-2 border-[var(--color-border-strong)] bg-[var(--color-bg)] p-4 font-bold text-white outline-none focus:border-[var(--color-primary-light)]" placeholder="Add context, what you tried, and where you are confused." />
          {errors.body ? <span className="mt-1 block text-sm font-bold text-[var(--color-danger)]">{errors.body}</span> : null}
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Tags" value={form.tags} error={errors.tag_names} onChange={(value) => updateField('tags', value)} placeholder="Java, OOP, Programming" />
          <Field label="Subject" value={form.subject} error={errors.subject} onChange={(value) => updateField('subject', value)} placeholder="Java" />
        </div>
        {createdQuestion?.slug ? <p className="border border-[var(--color-success)] bg-[color-mix(in_srgb,var(--color-success)_12%,var(--color-surface))] p-3 font-black text-[var(--color-success)]">Question posted successfully. <a href={`/questions/${createdQuestion.slug}`} className="underline">View question</a></p> : null}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={posting}>{posting ? 'Posting...' : 'Post Question'}</Button>
          <Button type="button" variant="dark" onClick={() => navigate('/community')}>Cancel</Button>
        </div>
      </form>
      </div>
      {toast ? <Toast {...toast} onDismiss={() => setToast(null)} /> : null}
    </>
  )
}

function Field({ label, value, error, onChange, placeholder }) {
  return (
    <label className="block">
      <span className="font-black text-white">{label}</span>
      <input required value={value} onChange={(event) => onChange(event.target.value)} className="mt-2 h-12 w-full border-2 border-[var(--color-border-strong)] bg-[var(--color-bg)] px-4 font-bold text-white outline-none focus:border-[var(--color-primary-light)]" placeholder={placeholder} />
      {error ? <span className="mt-1 block text-sm font-bold text-[var(--color-danger)]">{error}</span> : null}
    </label>
  )
}

export default AskQuestion

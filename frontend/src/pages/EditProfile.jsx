import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getApiErrorMessage, getCurrentProfile, listAcademicLevels, listCourses, listEducationBackgrounds, updateProfile } from '../api'
import Button from '../components/common/Button'
import { useAuth } from '../auth/useAuth'

const emptyForm = {
  displayName: '',
  bio: '',
  avatarUrl: '',
  college: '',
  educationBackgroundId: '',
  courseId: '',
  academicLevelId: '',
}

function EditProfile() {
  const navigate = useNavigate()
  const { status: authStatus, user: currentUser, refreshUser } = useAuth()
  const [form, setForm] = useState(emptyForm)
  const [backgrounds, setBackgrounds] = useState([])
  const [courses, setCourses] = useState([])
  const [levels, setLevels] = useState([])
  const [coursesForBackground, setCoursesForBackground] = useState('')
  const [levelsForCourse, setLevelsForCourse] = useState('')
  const [pageState, setPageState] = useState('loading')
  const [saveState, setSaveState] = useState('idle')
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true
    Promise.all([getCurrentProfile(), listEducationBackgrounds()]).then(
      ([profileResult, backgroundResult]) => {
        if (!active) return
        const { profile } = profileResult
        setForm({
          displayName: profile.displayName,
          bio: profile.bio,
          avatarUrl: profile.avatarUrl,
          college: profile.college,
          educationBackgroundId: profile.educationBackgroundId ? String(profile.educationBackgroundId) : '',
          courseId: profile.courseId ? String(profile.courseId) : '',
          academicLevelId: profile.academicLevelId ? String(profile.academicLevelId) : '',
        })
        setBackgrounds(backgroundResult)
        setPageState('success')
      },
      (nextError) => {
        if (!active) return
        setError(nextError)
        setPageState('error')
      },
    )
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!form.educationBackgroundId) {
      return undefined
    }
    let active = true
    listCourses(form.educationBackgroundId).then(
      (result) => { if (active) { setCourses(result); setCoursesForBackground(form.educationBackgroundId) } },
      (nextError) => { if (active) setError(nextError) },
    )
    return () => { active = false }
  }, [form.educationBackgroundId])

  useEffect(() => {
    if (!form.courseId) {
      return undefined
    }
    let active = true
    listAcademicLevels(form.courseId).then(
      (result) => { if (active) { setLevels(result); setLevelsForCourse(form.courseId) } },
      (nextError) => { if (active) setError(nextError) },
    )
    return () => { active = false }
  }, [form.courseId])

  if (authStatus !== 'authenticated') {
    return <ProfileMessage title="Sign in required" message="Sign in to edit your profile." action={<Button to="/login">Sign in</Button>} />
  }
  if (pageState === 'loading') return <ProfileMessage title="Loading profile" message="Fetching your profile details..." />
  if (pageState === 'error') return <ProfileMessage title="Unable to load profile" message={getApiErrorMessage(error)} action={<Button to="/profile">Back to profile</Button>} />

  const updateField = (field, value) => {
    setForm((current) => {
      const next = { ...current, [field]: value }
      if (field === 'educationBackgroundId') {
        next.courseId = ''
        next.academicLevelId = ''
      }
      if (field === 'courseId') next.academicLevelId = ''
      return next
    })
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaveState('loading')
    setError(null)
    try {
      await updateProfile(currentUser.username, {
        display_name: form.displayName.trim(),
        bio: form.bio.trim(),
        avatar_url: form.avatarUrl.trim(),
        college: form.college.trim(),
        education_background: form.educationBackgroundId ? Number(form.educationBackgroundId) : null,
        course: form.courseId ? Number(form.courseId) : null,
        academic_level: form.academicLevelId ? Number(form.academicLevelId) : null,
      })
      await refreshUser()
      navigate('/profile', { replace: true })
    } catch (nextError) {
      setError(nextError)
      setSaveState('error')
    }
  }

  return <main className="mx-auto w-full max-w-[900px] px-5 py-8 sm:px-8 lg:px-10">
    <div className="mb-6 flex items-center justify-between gap-4">
      <div><h1 className="text-3xl font-black text-white">Edit Profile</h1><p className="mt-2 text-sm text-[var(--color-text)]">Update the profile information shown to the StudyMate community.</p></div>
      <Link to="/profile" className="text-sm font-semibold text-[#55b7ee] hover:text-white">Cancel</Link>
    </div>
    <form onSubmit={handleSubmit} className="space-y-6 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 sm:p-7">
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Display name" value={form.displayName} onChange={(value) => updateField('displayName', value)} />
        <Field label="College" value={form.college} onChange={(value) => updateField('college', value)} />
      </div>
      <Field label="Avatar URL" type="url" value={form.avatarUrl} onChange={(value) => updateField('avatarUrl', value)} />
      <label className="block text-sm font-semibold text-white">Bio<textarea value={form.bio} onChange={(event) => updateField('bio', event.target.value)} maxLength={1000} rows={4} className="mt-2 block w-full border-2 border-[var(--color-border)] bg-[var(--color-band)] px-3 py-2 text-sm text-white outline-none focus:border-[#55b7ee]" /></label>
      <div className="grid gap-5 sm:grid-cols-3">
        <SelectField label="Education background" value={form.educationBackgroundId} onChange={(value) => updateField('educationBackgroundId', value)} options={backgrounds} placeholder="Select background" />
        <SelectField label="Course" value={form.courseId} onChange={(value) => updateField('courseId', value)} options={courses} placeholder="Select course" disabled={!form.educationBackgroundId || coursesForBackground !== form.educationBackgroundId} />
        <SelectField label="Academic level" value={form.academicLevelId} onChange={(value) => updateField('academicLevelId', value)} options={levels} placeholder="Select level" disabled={!form.courseId || levelsForCourse !== form.courseId} />
      </div>
      {error ? <p className="text-sm text-red-300" role="alert">{getApiErrorMessage(error)}</p> : null}
      <div className="flex justify-end"><Button type="submit" disabled={saveState === 'loading'}>{saveState === 'loading' ? 'Saving...' : 'Save changes'}</Button></div>
    </form>
  </main>
}

function Field({ label, value, onChange, type = 'text', required = false }) {
  return <label className="block text-sm font-semibold text-white">{label}<input type={type} value={value} onChange={(event) => onChange(event.target.value)} required={required} maxLength={type === 'url' ? undefined : 120} className="mt-2 block min-h-11 w-full border-2 border-[var(--color-border)] bg-[var(--color-band)] px-3 text-sm text-white outline-none focus:border-[#55b7ee]" /></label>
}

function SelectField({ label, value, onChange, options, placeholder, disabled = false }) {
  return <label className="block text-sm font-semibold text-white">{label}<select value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled} className="mt-2 block min-h-11 w-full border-2 border-[var(--color-border)] bg-[var(--color-band)] px-2 text-sm text-white outline-none focus:border-[#55b7ee] disabled:opacity-60"><option value="">{placeholder}</option>{options.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}</select></label>
}

function ProfileMessage({ title, message, action = null }) {
  return <main className="mx-auto flex min-h-[calc(100svh-13rem)] w-full max-w-[900px] items-center justify-center px-5 py-12 text-center"><section><h1 className="text-2xl font-black text-white">{title}</h1><p className="mt-3 text-sm text-[var(--color-text)]">{message}</p>{action ? <div className="mt-5">{action}</div> : null}</section></main>
}

export default EditProfile

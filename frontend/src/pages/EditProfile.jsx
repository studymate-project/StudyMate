import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ACADEMIC_STAGE_TYPES, getApiErrorMessage, listAcademicLevels, listCourses, listEducationBackgrounds, updateProfile } from '../api'
import Button from '../components/common/Button'
import Spinner from '../components/common/Spinner'
import { useAuth } from '../auth/useAuth'

const emptyForm = {
  displayName: '',
  bio: '',
  avatarUrl: '',
  college: '',
  country: '',
  state: '',
  city: '',
  educationBackgroundId: '',
  customBackground: '',
  courseId: '',
  customCourse: '',
  academicLevelId: '',
  academicLevelType: '',
  academicLevelValue: '',
}

function isOtherOption(option) {
  return option && (option.slug?.toLowerCase() === 'other' || option.name?.toLowerCase() === 'other')
}

function EditProfile() {
  const navigate = useNavigate()
  const { status: authStatus, user: currentUser, refreshUser } = useAuth()
  const [form, setForm] = useState(emptyForm)
  const [backgrounds, setBackgrounds] = useState([])
  const [courses, setCourses] = useState([])
  const [levels, setLevels] = useState([])
  const [catalogStatus, setCatalogStatus] = useState({ backgrounds: 'loading', courses: 'idle', levels: 'idle' })
  const [pageState, setPageState] = useState('loading')
  const [saveState, setSaveState] = useState('idle')
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!currentUser) return undefined
    let active = true
    const profile = currentUser.profile || {}

    listEducationBackgrounds().then((result) => {
      if (!active) return
      setForm({
        ...emptyForm,
        displayName: profile.display_name || '',
        bio: profile.bio || '',
        avatarUrl: profile.avatar_url || '',
        college: profile.college || '',
        country: profile.country || '',
        state: profile.state || '',
        city: profile.city || '',
        educationBackgroundId: profile.education_background ? String(profile.education_background) : '',
        customBackground: profile.custom_background || '',
        courseId: profile.course ? String(profile.course) : '',
        customCourse: profile.custom_course || '',
        academicLevelId: profile.academic_level ? String(profile.academic_level) : '',
        academicLevelType: profile.academic_level_type || '',
        academicLevelValue: profile.academic_level_value || '',
      })
      setBackgrounds(result)
      setCatalogStatus({
        backgrounds: 'success',
        courses: profile.education_background ? 'loading' : 'idle',
        levels: profile.course ? 'loading' : 'idle',
      })
      setPageState('success')
    }, (nextError) => {
      if (!active) return
      setError(nextError)
      setCatalogStatus((current) => ({ ...current, backgrounds: 'error' }))
      setPageState('error')
    })

    return () => { active = false }
  }, [currentUser])

  useEffect(() => {
    if (!form.educationBackgroundId) {
      return undefined
    }
    let active = true
    listCourses(form.educationBackgroundId).then((result) => {
      if (!active) return
      setCourses(result)
      setCatalogStatus((current) => ({ ...current, courses: 'success' }))
    }, (nextError) => {
      if (active) {
        setError(nextError)
        setCatalogStatus((current) => ({ ...current, courses: 'error' }))
      }
    })
    return () => { active = false }
  }, [form.educationBackgroundId])

  useEffect(() => {
    if (!form.courseId) {
      return undefined
    }
    let active = true
    listAcademicLevels(form.courseId, form.educationBackgroundId).then((result) => {
      if (!active) return
      setLevels(result)
      setCatalogStatus((current) => ({ ...current, levels: 'success' }))
    }, (nextError) => {
      if (active) {
        setError(nextError)
        setCatalogStatus((current) => ({ ...current, levels: 'error' }))
      }
    })
    return () => { active = false }
  }, [form.courseId, form.educationBackgroundId])

  if (authStatus !== 'authenticated') {
    return <ProfileMessage title="Sign in required" message="Sign in to edit your profile." action={<Button to="/login">Sign in</Button>} />
  }
  if (pageState === 'loading') return <ProfileMessage loadingLabel="Loading profile" />
  if (pageState === 'error') return <ProfileMessage title="Unable to load profile" message={getApiErrorMessage(error)} action={<Button to="/profile">Back to profile</Button>} />

  const selectedBackground = backgrounds.find((background) => String(background.id) === form.educationBackgroundId)
  const selectedCourse = courses.find((course) => String(course.id) === form.courseId)
  const selectedCourseIsOther = isOtherOption(selectedCourse)
  const selectedBackgroundIsOther = isOtherOption(selectedBackground)
  const hasCustomStage = !form.academicLevelId
  const stageTypes = [...ACADEMIC_STAGE_TYPES]
  levels.forEach((level) => {
    if (level.level_type && !stageTypes.some((type) => type.value === level.level_type)) {
      stageTypes.push({ value: level.level_type, label: level.level_type })
    }
  })

  const updateField = (field, value) => {
    setForm((current) => {
      const next = { ...current, [field]: value }
      if (field === 'educationBackgroundId') {
        setCourses([])
        setLevels([])
        setCatalogStatus((current) => ({ ...current, courses: value ? 'loading' : 'idle', levels: 'idle' }))
        next.customBackground = ''
        next.courseId = ''
        next.customCourse = ''
        next.academicLevelId = ''
        next.academicLevelType = ''
        next.academicLevelValue = ''
      }
      if (field === 'courseId') {
        setLevels([])
        setCatalogStatus((current) => ({ ...current, levels: value ? 'loading' : 'idle' }))
        next.customCourse = ''
        next.academicLevelId = ''
        next.academicLevelType = ''
        next.academicLevelValue = ''
      }
      if (field === 'academicLevelId' && value) {
        next.academicLevelType = ''
        next.academicLevelValue = ''
      }
      return next
    })
    setError(null)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSaveState('loading')
    setError(null)
    const nextErrors = {}
    if (selectedBackgroundIsOther && !form.customBackground.trim()) nextErrors.customBackground = 'Enter your custom educational background.'
    if (selectedCourseIsOther && !form.customCourse.trim()) nextErrors.customCourse = 'Enter your custom course or program.'
    if (hasCustomStage && (!form.academicLevelType || !form.academicLevelValue.trim())) nextErrors.academicLevelValue = 'Enter your academic stage and stage type.'
    if (Object.keys(nextErrors).length) {
      setError({ message: Object.values(nextErrors).join(' ') })
      setSaveState('idle')
      return
    }

    const payload = {
      display_name: form.displayName.trim(),
      bio: form.bio.trim(),
      avatar_url: form.avatarUrl.trim(),
      college: form.college.trim(),
      country: form.country.trim(),
      state: form.state.trim(),
      city: form.city.trim(),
      education_background: form.educationBackgroundId ? Number(form.educationBackgroundId) : null,
      custom_background: form.customBackground.trim(),
      course: form.courseId ? Number(form.courseId) : null,
      custom_course: form.customCourse.trim(),
      academic_level: form.academicLevelId ? Number(form.academicLevelId) : null,
    }
    if (hasCustomStage) {
      payload.academic_level_type = form.academicLevelType
      payload.academic_level_value = form.academicLevelValue.trim()
    }

    try {
      await updateProfile(currentUser.username, payload)
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
      <Link to="/profile" className="text-sm font-semibold text-[var(--color-text)] hover:text-white">Cancel</Link>
    </div>
    <form onSubmit={handleSubmit} className="space-y-6 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 sm:p-7">
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Display name" value={form.displayName} onChange={(value) => updateField('displayName', value)} />
        <Field label="College / University" value={form.college} onChange={(value) => updateField('college', value)} />
      </div>
      <div className="grid gap-5 sm:grid-cols-3">
        <Field label="Country" value={form.country} onChange={(value) => updateField('country', value)} />
        <Field label="State" value={form.state} onChange={(value) => updateField('state', value)} />
        <Field label="City" value={form.city} onChange={(value) => updateField('city', value)} />
      </div>
      <Field label="Avatar URL" type="url" value={form.avatarUrl} onChange={(value) => updateField('avatarUrl', value)} />
      <label className="block text-sm font-semibold text-white">Bio<textarea value={form.bio} onChange={(event) => updateField('bio', event.target.value)} maxLength={1000} rows={4} className="mt-2 block w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-band)] px-3 py-2 text-sm text-white outline-none focus:border-[var(--color-focus)]" /></label>
      <div className="grid gap-5 sm:grid-cols-3">
        <SelectField label="Education background" value={form.educationBackgroundId} onChange={(value) => updateField('educationBackgroundId', value)} options={backgrounds} placeholder="Select background" loading={catalogStatus.backgrounds === 'loading'} disabled={catalogStatus.backgrounds !== 'success'} />
        <SelectField label="Course / program" value={form.courseId} onChange={(value) => updateField('courseId', value)} options={courses} placeholder="Select course" loading={catalogStatus.courses === 'loading'} disabled={!form.educationBackgroundId || catalogStatus.courses !== 'success'} />
        <SelectField label="Academic level / stage" value={form.academicLevelId} onChange={(value) => updateField('academicLevelId', value)} options={levels} placeholder="Select level" loading={catalogStatus.levels === 'loading'} disabled={!form.courseId || catalogStatus.levels !== 'success'} />
      </div>
      {selectedBackgroundIsOther || form.customBackground ? <Field label="Custom educational background" value={form.customBackground} onChange={(value) => updateField('customBackground', value)} error={error?.data?.custom_background} /> : null}
      {selectedCourseIsOther || form.customCourse ? <Field label="Custom course / program" value={form.customCourse} onChange={(value) => updateField('customCourse', value)} error={error?.data?.custom_course} maxLength={160} /> : null}
      {hasCustomStage ? <div className="grid gap-5 sm:grid-cols-2"><SelectField label="Stage type" value={form.academicLevelType} onChange={(value) => updateField('academicLevelType', value)} options={stageTypes} placeholder="Select stage type" /><Field label="Academic level / stage" value={form.academicLevelValue} onChange={(value) => updateField('academicLevelValue', value)} error={error?.data?.academic_level_value} /></div> : null}
      {error ? <p className="text-sm text-[var(--color-danger)]" role="alert">{getApiErrorMessage(error)}</p> : null}
      <div className="flex justify-end"><Button type="submit" disabled={saveState === 'loading'}>{saveState === 'loading' ? 'Saving...' : 'Save changes'}</Button></div>
    </form>
  </main>
}

function Field({ label, value, onChange, type = 'text', required = false, error = '', maxLength = 120 }) {
  return <label className="block text-sm font-semibold text-white">{label}<input type={type} value={value} onChange={(event) => onChange(event.target.value)} required={required} maxLength={type === 'url' ? undefined : maxLength} className={`mt-2 block min-h-11 w-full rounded-lg border ${error ? 'border-[var(--color-danger)]' : 'border-[var(--color-border)]'} bg-[var(--color-band)] px-3 text-sm text-white outline-none focus:border-[var(--color-focus)]`} />{error ? <span className="mt-1 block text-xs font-normal text-[var(--color-danger)]">{error}</span> : null}</label>
}

function SelectField({ label, value, onChange, options, placeholder, disabled = false, loading = false }) {
  return <label className="block text-sm font-semibold text-white">{label}<select value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled} className="mt-2 block min-h-11 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-band)] px-2 text-sm text-white outline-none focus:border-[var(--color-focus)] disabled:opacity-60"><option value="">{loading ? 'Loading...' : placeholder}</option>{options.map((option) => <option key={option.id || option.value} value={option.id || option.value}>{option.name || option.label}</option>)}</select></label>
}

function ProfileMessage({ title, message, action = null, loadingLabel = '' }) {
  return <main className="mx-auto flex min-h-[calc(100svh-13rem)] w-full max-w-[900px] items-center justify-center px-5 py-12 text-center">{loadingLabel ? <Spinner label={loadingLabel} /> : <section><h1 className="text-2xl font-black text-white">{title}</h1><p className="mt-3 text-sm text-[var(--color-text)]">{message}</p>{action ? <div className="mt-5">{action}</div> : null}</section>}</main>
}

export default EditProfile

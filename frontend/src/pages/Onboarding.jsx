import { CircleCheckBig } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import { ACADEMIC_STAGE_TYPES, listAcademicLevels, listCourses, listEducationBackgrounds, submitOnboarding } from '../api/onboarding'
import { useAuth } from '../auth/useAuth'
import Spinner from '../components/common/Spinner'
import { Navigation, OnboardingHeader, SelectionCard } from '../components/onboarding/OnboardingPrimitives'
import './Onboarding.css'

const STORAGE_KEY = 'studyMate_onboarding_draft'
function emptyProfile(userProfile = {}) {
  return {
    educationBackground: userProfile.education_background ? { id: userProfile.education_background } : null,
    customBackground: userProfile.custom_background || '',
    course: userProfile.course ? { id: userProfile.course } : null,
    customCourse: userProfile.custom_course || '',
    academicLevel: userProfile.academic_level ? { id: userProfile.academic_level } : null,
    academicLevelType: userProfile.academic_level_type || '',
    academicLevelValue: userProfile.academic_level_value || '',
    country: userProfile.country || '',
    state: userProfile.state || '',
    city: userProfile.city || '',
  }
}

function emptyCatalogState(status = 'idle') {
  return { status, data: [], error: null }
}

function readDraft(storageKey, userProfile) {
  const fallback = emptyProfile(userProfile)
  try {
    const saved = sessionStorage.getItem(storageKey)
    const parsed = saved ? JSON.parse(saved) : null
    const savedProfile = parsed?.profile
    return {
      step: Math.min(4, Math.max(1, Number(parsed?.step) || 1)),
      profile: { ...fallback, ...(savedProfile || {}) },
    }
  } catch {
    return { step: 1, profile: fallback }
  }
}

function sameId(first, second) {
  return String(first) === String(second)
}

function isOtherOption(option) {
  return option && (option.slug?.toLowerCase() === 'other' || option.name?.toLowerCase() === 'other')
}

function CatalogState({ state, loadingMessage, emptyMessage, onRetry }) {
  if (state.status === 'loading') return <div className="selection-count flex justify-center"><Spinner label={loadingMessage} /></div>
  if (state.status === 'error') {
    return <div className="selection-count" role="alert"><p>{getApiErrorMessage(state.error)}</p><button type="button" onClick={onRetry} className="mt-2 underline">Try again</button></div>
  }
  if (state.status === 'success' && !state.data.length) return <p className="selection-count" role="status">{emptyMessage}</p>
  return null
}

function getLevelCopy(levels) {
  const type = levels[0]?.level_type
  const copyByType = {
    class: { title: 'Which class are you in?', helper: 'Help us show subjects that fit your class' },
    semester: { title: 'Which semester are you in?', helper: 'Help us show you the most relevant resources' },
    year: { title: 'Which year are you in?', helper: 'Help us tailor your learning path' },
    stage: { title: 'Which stage are you in?', helper: 'Help us tailor your learning path' },
    level: { title: 'What is your current level?', helper: 'Help us tailor your learning path' },
    other: { title: 'What best describes your current level?', helper: 'We will use this to refine recommendations' },
  }
  return copyByType[type] || { title: 'What is your academic level or stage?', helper: 'Choose a catalog option or enter your own stage' }
}

function Onboarding() {
  const navigate = useNavigate()
  const { user, updateUser } = useAuth()
  const storageKey = `${STORAGE_KEY}_${user?.id || 'current'}`
  const [draft] = useState(() => readDraft(storageKey, user?.profile))
  const [step, setStep] = useState(draft.step)
  const [profile, setProfile] = useState(draft.profile)
  const [submissionError, setSubmissionError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [customStageSelected, setCustomStageSelected] = useState(Boolean(!draft.profile.academicLevel && (draft.profile.academicLevelType || draft.profile.academicLevelValue)))
  const [backgroundRetry, setBackgroundRetry] = useState(0)
  const [courseRetry, setCourseRetry] = useState(0)
  const [levelRetry, setLevelRetry] = useState(0)
  const [backgroundState, setBackgroundState] = useState(() => emptyCatalogState('loading'))
  const [courseState, setCourseState] = useState(() => emptyCatalogState(draft.profile.educationBackground ? 'loading' : 'idle'))
  const [levelState, setLevelState] = useState(() => emptyCatalogState(draft.profile.course ? 'loading' : 'idle'))

  const isComplete = user?.profile?.onboarding_completed === true
  const backgroundId = profile.educationBackground?.id
  const courseId = profile.course?.id
  const levelCopy = getLevelCopy(levelState.data)
  const selectedBackgroundIsOther = isOtherOption(profile.educationBackground)
  const selectedCourseIsOther = isOtherOption(profile.course)
  const hasCustomStage = !profile.academicLevel && (customStageSelected || !levelState.data.length)
  const hasBackgroundValue = Boolean(profile.educationBackground && (!selectedBackgroundIsOther || profile.customBackground.trim()))
  const hasCourseValue = Boolean((profile.course || profile.customCourse.trim()) && (!selectedCourseIsOther || profile.customCourse.trim()))
  const canContinueFromStepOne = Boolean(hasBackgroundValue && hasCourseValue)
  const canContinueFromStepTwo = Boolean(profile.academicLevel || (hasCustomStage && profile.academicLevelType && profile.academicLevelValue.trim()))

  useEffect(() => {
    let active = true

    listEducationBackgrounds().then((data) => {
      if (!active) return
      setBackgroundState({ status: 'success', data, error: null })
      setProfile((current) => {
        if (!current.educationBackground) return current
        const background = data.find((item) => sameId(item.id, current.educationBackground.id))
        return background
          ? { ...current, educationBackground: background }
          : { ...current, educationBackground: null, course: null, academicLevel: null }
      })
    }, (error) => {
      if (active) setBackgroundState({ status: 'error', data: [], error })
    })

    return () => { active = false }
  }, [backgroundRetry])

  useEffect(() => {
    if (!backgroundId) {
      return undefined
    }
    let active = true

    listCourses(backgroundId).then((data) => {
      if (!active) return
      setCourseState({ status: 'success', data, error: null })
      setProfile((current) => {
        if (!current.course) return current
        const course = data.find((item) => sameId(item.id, current.course.id))
        return course ? { ...current, course } : { ...current, course: null, academicLevel: null, academicLevelType: '', academicLevelValue: '' }
      })
    }, (error) => {
      if (active) setCourseState({ status: 'error', data: [], error })
    })

    return () => { active = false }
  }, [backgroundId, courseRetry])

  useEffect(() => {
    if (!courseId) {
      return undefined
    }
    let active = true

    listAcademicLevels(courseId, backgroundId).then((data) => {
      if (!active) return
      setLevelState({ status: 'success', data, error: null })
      setProfile((current) => {
        if (!current.academicLevel) return current
        const academicLevel = data.find((item) => sameId(item.id, current.academicLevel.id))
        return academicLevel
          ? { ...current, academicLevel, academicLevelType: '', academicLevelValue: '' }
          : { ...current, academicLevel: null }
      })
    }, (error) => {
      if (active) setLevelState({ status: 'error', data: [], error })
    })

    return () => { active = false }
  }, [courseId, backgroundId, levelRetry])

  useEffect(() => {
    sessionStorage.setItem(storageKey, JSON.stringify({ step, profile }))
  }, [storageKey, step, profile])

  if (isComplete) return <Navigate to="/home" replace />

  const selectEducation = (educationBackground) => {
    setProfile((current) => ({
      ...emptyProfile({ country: current.country, state: current.state, city: current.city }),
      educationBackground,
    }))
    setCourseState(emptyCatalogState('loading'))
    setLevelState(emptyCatalogState())
    setCustomStageSelected(false)
    setSubmissionError(null)
  }

  const selectCourse = (course) => {
    setProfile((current) => ({
      ...current,
      course,
      customCourse: '',
      academicLevel: null,
      academicLevelType: '',
      academicLevelValue: '',
    }))
    setLevelState(emptyCatalogState('loading'))
    setCustomStageSelected(false)
    setSubmissionError(null)
  }

  const selectLevel = (academicLevel) => {
    setProfile((current) => ({ ...current, academicLevel, academicLevelType: '', academicLevelValue: '' }))
    setCustomStageSelected(false)
    setSubmissionError(null)
  }

  const updateProfileField = (field, value) => {
    setProfile((current) => ({ ...current, [field]: value }))
    setSubmissionError(null)
  }

  const useCustomStage = () => {
    setProfile((current) => ({
      ...current,
      academicLevel: null,
      academicLevelType: current.academicLevelType || 'stage',
      academicLevelValue: current.academicLevelValue || '',
    }))
    setCustomStageSelected(true)
  }

  const finish = async () => {
    if (!canContinueFromStepOne || !canContinueFromStepTwo) return

    setIsSubmitting(true)
    setSubmissionError(null)
    const payload = {
      education_background: profile.educationBackground?.id || null,
      custom_background: profile.customBackground.trim(),
      course: profile.course?.id || null,
      custom_course: profile.customCourse.trim(),
      academic_level: profile.academicLevel?.id || null,
      country: profile.country.trim(),
      state: profile.state.trim(),
      city: profile.city.trim(),
    }
    if (!profile.academicLevel) {
      payload.academic_level_type = profile.academicLevelType
      payload.academic_level_value = profile.academicLevelValue.trim()
    }

    try {
      const response = await submitOnboarding(payload)
      if (response?.profile && user) updateUser({ ...user, profile: response.profile })
      sessionStorage.removeItem(storageKey)
      navigate('/home', { replace: true })
    } catch (error) {
      setSubmissionError(error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const renderReviewValue = (value) => value ? <span>{value}</span> : null
  const backgroundValue = profile.customBackground.trim()
    ? `${profile.educationBackground?.name || 'Other'}: ${profile.customBackground.trim()}`
    : profile.educationBackground?.name
  const courseValue = profile.customCourse.trim()
    ? `${profile.course?.name || 'Other'}: ${profile.customCourse.trim()}`
    : profile.course?.name
  const stageValue = profile.academicLevel?.name || profile.academicLevelValue.trim()
  const locationValue = [profile.city, profile.state, profile.country].map((value) => value.trim()).filter(Boolean).join(', ')

  const stepContent = {
    1: <section className="onboarding-step" key="education">
      <div className="onboarding-copy"><h1>What are you studying?</h1><p>We&apos;ll personalize your StudyMate experience</p></div>
      <fieldset className="onboarding-fieldset"><legend>Select your educational background</legend><div className="selection-list" role="radiogroup" aria-label="Educational background">
        {backgroundState.data.map((background) => <SelectionCard key={background.id} selected={sameId(profile.educationBackground?.id, background.id)} onClick={() => selectEducation(background)}>{background.name}</SelectionCard>)}
      </div><CatalogState state={backgroundState} loadingMessage="Loading educational backgrounds..." emptyMessage="No educational backgrounds are available yet." onRetry={() => { setBackgroundState(emptyCatalogState('loading')); setBackgroundRetry((retry) => retry + 1) }} /></fieldset>
      {selectedBackgroundIsOther ? <label className="onboarding-text-field" htmlFor="custom-background">Tell us your educational background<input id="custom-background" value={profile.customBackground} onChange={(event) => updateProfileField('customBackground', event.target.value)} placeholder="For example, independent study" maxLength={120} /></label> : null}
      {backgroundId ? <fieldset className="onboarding-fieldset course-fieldset"><legend>Choose your course or program</legend><div className="course-grid" role="radiogroup" aria-label="Course or program">
        {courseState.data.map((course) => <SelectionCard key={course.id} selected={sameId(profile.course?.id, course.id)} onClick={() => selectCourse(course)} type="radio">{course.name}</SelectionCard>)}
      </div><CatalogState state={courseState} loadingMessage="Loading courses and programs..." emptyMessage="No courses are available for this background." onRetry={() => { setCourseState(emptyCatalogState('loading')); setCourseRetry((retry) => retry + 1) }} /></fieldset> : null}
      {selectedCourseIsOther ? <label className="onboarding-text-field" htmlFor="custom-course">Tell us your course or program<input id="custom-course" value={profile.customCourse} onChange={(event) => updateProfileField('customCourse', event.target.value)} placeholder="For example, a specialist program" maxLength={160} /></label> : null}
      <Navigation onNext={() => setStep(2)} nextDisabled={!canContinueFromStepOne} />
    </section>,
    2: <section className="onboarding-step" key="level">
      <div className="onboarding-copy"><h1>{levelCopy.title}</h1><p>{levelCopy.helper}</p></div>
      <div className="level-grid" role="radiogroup" aria-label={levelCopy.title}>
        {levelState.data.map((level) => <SelectionCard key={level.id} selected={sameId(profile.academicLevel?.id, level.id)} onClick={() => selectLevel(level)} type="radio">{level.name}</SelectionCard>)}
      </div>
      <CatalogState state={levelState} loadingMessage="Loading academic levels..." emptyMessage="No catalog stages are available for this course. Enter your stage below." onRetry={() => { setLevelState(emptyCatalogState('loading')); setLevelRetry((retry) => retry + 1) }} />
      {levelState.status === 'success' && levelState.data.length && !profile.academicLevel ? <button type="button" className="onboarding-custom-choice" onClick={useCustomStage}>Use a custom stage</button> : null}
      {hasCustomStage ? <div className="onboarding-custom-stage">
        <label className="onboarding-text-field" htmlFor="academic-level-type">Stage type<select id="academic-level-type" value={profile.academicLevelType} onChange={(event) => updateProfileField('academicLevelType', event.target.value)}><option value="">Select a stage type</option>{ACADEMIC_STAGE_TYPES.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}</select></label>
        <label className="onboarding-text-field" htmlFor="academic-level-value">Your academic level or stage<input id="academic-level-value" value={profile.academicLevelValue} onChange={(event) => updateProfileField('academicLevelValue', event.target.value)} placeholder="For example, 2nd Year or Portfolio Stage" maxLength={120} /></label>
      </div> : null}
      <Navigation onBack={() => setStep(1)} onNext={() => setStep(3)} nextDisabled={!canContinueFromStepTwo} />
    </section>,
    3: <section className="onboarding-step" key="location">
      <div className="onboarding-copy"><h1>Where are you based?</h1><p>Add your location to complete your profile. You can edit it later.</p></div>
      <div className="onboarding-location-grid">
        <label className="onboarding-text-field" htmlFor="country">Country<input id="country" value={profile.country} onChange={(event) => updateProfileField('country', event.target.value)} placeholder="India" maxLength={120} /></label>
        <label className="onboarding-text-field" htmlFor="state">State<input id="state" value={profile.state} onChange={(event) => updateProfileField('state', event.target.value)} placeholder="Delhi" maxLength={120} /></label>
        <label className="onboarding-text-field" htmlFor="city">City<input id="city" value={profile.city} onChange={(event) => updateProfileField('city', event.target.value)} placeholder="New Delhi" maxLength={120} /></label>
      </div>
      <Navigation onBack={() => setStep(2)} onNext={() => setStep(4)} />
    </section>,
    4: <section className="onboarding-step onboarding-review" key="review">
      <div className="ready-icon" aria-hidden="true"><CircleCheckBig size={33} /></div>
      <div className="onboarding-copy"><h1>Your StudyMate is ready!</h1><p>Review your profile before you start learning</p></div>
      <section className="profile-summary" aria-labelledby="profile-summary-title"><h2 id="profile-summary-title">Your profile</h2><dl className="profile-review-list">
        {backgroundValue ? <ReviewRow label="Educational background">{renderReviewValue(backgroundValue)}</ReviewRow> : null}
        {courseValue ? <ReviewRow label="Course or program">{renderReviewValue(courseValue)}</ReviewRow> : null}
        {stageValue ? <ReviewRow label="Academic level or stage">{renderReviewValue(stageValue)}</ReviewRow> : null}
        {locationValue ? <ReviewRow label="Location">{renderReviewValue(locationValue)}</ReviewRow> : null}
      </dl></section>
      {submissionError ? <p className="selection-count" role="alert">{submissionError.status === 401 ? 'Your session has expired. Please sign in again.' : getApiErrorMessage(submissionError)}</p> : null}
      <Navigation onBack={() => setStep(3)} onNext={finish} final loading={isSubmitting} nextDisabled={!canContinueFromStepOne || !canContinueFromStepTwo} />
    </section>,
  }

  return <main className="onboarding-page"><div className="onboarding-shell"><OnboardingHeader step={step} />{stepContent[step]}</div></main>
}

function ReviewRow({ label, children }) {
  return <div className="profile-review-row"><dt>{label}</dt><dd>{children}</dd></div>
}

export default Onboarding

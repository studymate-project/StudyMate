import { Check, CircleCheckBig } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../api/errors'
import { listAcademicLevels, listCourses, listEducationBackgrounds, listInterests, submitOnboarding } from '../api/onboarding'
import { useAuth } from '../auth/useAuth'
import Spinner from '../components/common/Spinner'
import { Navigation, OnboardingHeader, RecommendationCard, SelectionCard } from '../components/onboarding/OnboardingPrimitives'
import './Onboarding.css'

const STORAGE_KEY = 'studyMate_onboarding_draft'

function emptyProfile() {
  return { educationBackground: null, course: null, academicLevel: null, interests: [] }
}

function emptyCatalogState(status = 'idle') {
  return { status, data: [], error: null }
}

function readDraft(storageKey) {
  try {
    const saved = sessionStorage.getItem(storageKey)
    const parsed = saved ? JSON.parse(saved) : null
    const savedProfile = parsed?.profile
    if (!savedProfile || !savedProfile.educationBackground) return { step: 1, profile: emptyProfile() }

    return {
      step: Math.min(4, Math.max(1, Number(parsed.step) || 1)),
      profile: {
        ...emptyProfile(),
        ...savedProfile,
        interests: Array.isArray(savedProfile.interests) ? savedProfile.interests : [],
      },
    }
  } catch {
    return { step: 1, profile: emptyProfile() }
  }
}

function sameId(first, second) {
  return String(first) === String(second)
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
  return copyByType[type] || { title: 'What is your academic level?', helper: 'Help us tailor your learning path' }
}

function Onboarding() {
  const navigate = useNavigate()
  const { user, updateUser } = useAuth()
  const storageKey = `${STORAGE_KEY}_${user?.id || 'current'}`
  const [draft] = useState(() => readDraft(storageKey))
  const [step, setStep] = useState(draft.step)
  const [profile, setProfile] = useState(draft.profile)
  const [interestNotice, setInterestNotice] = useState('')
  const [customInterest, setCustomInterest] = useState('')
  const [submissionError, setSubmissionError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [backgroundRetry, setBackgroundRetry] = useState(0)
  const [courseRetry, setCourseRetry] = useState(0)
  const [levelRetry, setLevelRetry] = useState(0)
  const [interestRetry, setInterestRetry] = useState(0)
  const [backgroundState, setBackgroundState] = useState(() => emptyCatalogState('loading'))
  const [courseState, setCourseState] = useState(() => emptyCatalogState(draft.profile.educationBackground ? 'loading' : 'idle'))
  const [levelState, setLevelState] = useState(() => emptyCatalogState(draft.profile.course ? 'loading' : 'idle'))
  const [interestState, setInterestState] = useState(() => emptyCatalogState(draft.profile.course ? 'loading' : 'idle'))

  const isComplete = user?.profile?.onboarding_completed === true
  const backgroundId = profile.educationBackground?.id
  const courseId = profile.course?.id
  const levelCopy = getLevelCopy(levelState.data)

  useEffect(() => {
    let active = true

    listEducationBackgrounds().then((data) => {
      if (!active) return
      setBackgroundState({ status: 'success', data, error: null })
      setProfile((current) => {
        if (!current.educationBackground) return current
        const background = data.find((item) => sameId(item.id, current.educationBackground.id))
        return background ? { ...current, educationBackground: background } : emptyProfile()
      })
    }, (error) => {
      if (active) setBackgroundState({ status: 'error', data: [], error })
    })

    return () => { active = false }
  }, [backgroundRetry])

  useEffect(() => {
    if (!backgroundId) return undefined
    let active = true

    listCourses(backgroundId).then((data) => {
      if (!active) return
      setCourseState({ status: 'success', data, error: null })
      setProfile((current) => {
        if (!current.course) return current
        const course = data.find((item) => sameId(item.id, current.course.id))
        return course ? { ...current, course } : { ...current, course: null, academicLevel: null, interests: [] }
      })
    }, (error) => {
      if (active) setCourseState({ status: 'error', data: [], error })
    })

    return () => { active = false }
  }, [backgroundId, courseRetry])

  useEffect(() => {
    if (!courseId) return undefined
    let active = true

    listAcademicLevels(courseId).then((data) => {
      if (!active) return
      setLevelState({ status: 'success', data, error: null })
      setProfile((current) => {
        if (!current.academicLevel) return current
        const academicLevel = data.find((item) => sameId(item.id, current.academicLevel.id))
        return academicLevel ? { ...current, academicLevel } : { ...current, academicLevel: null, interests: [] }
      })
    }, (error) => {
      if (active) setLevelState({ status: 'error', data: [], error })
    })

    return () => { active = false }
  }, [courseId, levelRetry])

  useEffect(() => {
    if (!courseId) return undefined
    let active = true

    listInterests(courseId).then((data) => {
      if (!active) return
      setInterestState({ status: 'success', data, error: null })
      setProfile((current) => ({
        ...current,
        interests: current.interests.filter((interest) => data.some((item) => sameId(item.id, interest.id))),
      }))
    }, (error) => {
      if (active) setInterestState({ status: 'error', data: [], error })
    })

    return () => { active = false }
  }, [courseId, interestRetry])

  useEffect(() => {
    sessionStorage.setItem(storageKey, JSON.stringify({ step, profile }))
  }, [storageKey, step, profile])

  if (isComplete) return <Navigate to="/home" replace />

  const selectEducation = (educationBackground) => {
    setProfile({ ...emptyProfile(), educationBackground })
    setCourseState(emptyCatalogState('loading'))
    setLevelState(emptyCatalogState())
    setInterestState(emptyCatalogState())
    setInterestNotice('')
    setSubmissionError(null)
  }

  const selectCourse = (course) => {
    setProfile((current) => ({ ...current, course, academicLevel: null, interests: [] }))
    setLevelState(emptyCatalogState('loading'))
    setInterestState(emptyCatalogState('loading'))
    setInterestNotice('')
  }

  const selectLevel = (academicLevel) => {
    setProfile((current) => ({ ...current, academicLevel, interests: [] }))
    setInterestNotice('')
  }

  const toggleInterest = (interest) => {
    setProfile((current) => {
      const isSelected = current.interests.some((item) => sameId(item.id, interest.id))
      if (isSelected) return { ...current, interests: current.interests.filter((item) => !sameId(item.id, interest.id)) }
      if (current.interests.length >= 8) {
        setInterestNotice('Choose up to 8 topics to keep your recommendations focused.')
        return current
      }
      setInterestNotice('')
      return { ...current, interests: [...current.interests, interest] }
    })
  }

  const addCustomInterest = () => {
    if (!customInterest.trim()) return
    setInterestNotice('Choose topics from the course catalog so your selections can be saved.')
    setCustomInterest('')
  }

  const finish = async () => {
    if (!profile.educationBackground?.id || !profile.course?.id || !profile.academicLevel?.id || !profile.interests.length) return

    setIsSubmitting(true)
    setSubmissionError(null)
    try {
      const response = await submitOnboarding({
        education_background: profile.educationBackground.id,
        course: profile.course.id,
        academic_level: profile.academicLevel.id,
        interests: profile.interests.map((interest) => interest.id),
      })
      if (response?.profile && user) updateUser({ ...user, profile: response.profile })
      sessionStorage.removeItem(storageKey)
      navigate('/home', { replace: true })
    } catch (error) {
      setSubmissionError(error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const selectedInterest = (interest) => profile.interests.some((item) => sameId(item.id, interest.id))
  const recommendations = profile.interests.slice(0, 3).map((interest) => ({
    topic: interest.name,
    title: interest.description || interest.name,
    type: 'Interest',
  }))

  const stepContent = {
    1: <section className="onboarding-step" key="education">
      <div className="onboarding-copy"><h1>What are you studying?</h1><p>We&apos;ll personalize your StudyMate experience</p></div>
      <fieldset className="onboarding-fieldset"><legend>Select your educational background</legend><div className="selection-list" role="radiogroup" aria-label="Educational background">
        {backgroundState.data.map((background) => <SelectionCard key={background.id} selected={sameId(profile.educationBackground?.id, background.id)} onClick={() => selectEducation(background)}>{background.name}</SelectionCard>)}
      </div><CatalogState state={backgroundState} loadingMessage="Loading educational backgrounds..." emptyMessage="No educational backgrounds are available yet." onRetry={() => { setBackgroundState(emptyCatalogState('loading')); setBackgroundRetry((retry) => retry + 1) }} /></fieldset>
      {backgroundId ? <fieldset className="onboarding-fieldset course-fieldset"><legend>Choose your course or program</legend><div className="course-grid" role="radiogroup" aria-label="Course or program">
        {courseState.data.map((course) => <SelectionCard key={course.id} selected={sameId(profile.course?.id, course.id)} onClick={() => selectCourse(course)} type="radio">{course.name}</SelectionCard>)}
      </div><CatalogState state={courseState} loadingMessage="Loading courses and programs..." emptyMessage="No courses are available for this background." onRetry={() => { setCourseState(emptyCatalogState('loading')); setCourseRetry((retry) => retry + 1) }} /></fieldset> : null}
      <Navigation onNext={() => setStep(2)} nextDisabled={!profile.educationBackground || !profile.course} />
    </section>,
    2: <section className="onboarding-step" key="level">
      <div className="onboarding-copy"><h1>{levelCopy.title}</h1><p>{levelCopy.helper}</p></div>
      <div className="level-grid" role="radiogroup" aria-label={levelCopy.title}>
        {levelState.data.map((level) => <SelectionCard key={level.id} selected={sameId(profile.academicLevel?.id, level.id)} onClick={() => selectLevel(level)} type="radio">{level.name}</SelectionCard>)}
      </div>
      <CatalogState state={levelState} loadingMessage="Loading academic levels..." emptyMessage="No academic levels are available for this course." onRetry={() => { setLevelState(emptyCatalogState('loading')); setLevelRetry((retry) => retry + 1) }} />
      <Navigation onBack={() => setStep(1)} onNext={() => setStep(3)} nextDisabled={!profile.academicLevel} />
    </section>,
    3: <section className="onboarding-step" key="interests">
      <div className="onboarding-copy"><h1>What are you interested in?</h1><p>Select topics you want to explore - choose multiple</p></div>
      <div className="interest-list" aria-label="Topics of interest">
        {interestState.data.map((interest) => <button key={interest.id} type="button" onClick={() => toggleInterest(interest)} className={`interest-chip ${selectedInterest(interest) ? 'is-selected' : ''}`} aria-pressed={selectedInterest(interest)}>{selectedInterest(interest) ? <Check size={14} strokeWidth={3} /> : null}{interest.name}</button>)}
      </div>
      <CatalogState state={interestState} loadingMessage="Loading topics for this course..." emptyMessage="No interests are available for this course." onRetry={() => { setInterestState(emptyCatalogState('loading')); setInterestRetry((retry) => retry + 1) }} />
      <form className="custom-interest-form" onSubmit={(event) => { event.preventDefault(); addCustomInterest() }}><label htmlFor="custom-interest">Don&apos;t see your interest?</label><div><input id="custom-interest" value={customInterest} onChange={(event) => setCustomInterest(event.target.value)} placeholder="Add a topic you want to explore" maxLength="60" /><button type="submit" disabled={!customInterest.trim()}>Add topic</button></div></form>
      <p className="selection-count" role="status">{profile.interests.length} selected{interestNotice ? ` - ${interestNotice}` : ''}</p>
      <Navigation onBack={() => setStep(2)} onNext={() => setStep(4)} nextDisabled={!profile.interests.length} />
    </section>,
    4: <section className="onboarding-step onboarding-review" key="review">
      <div className="ready-icon" aria-hidden="true"><CircleCheckBig size={33} /></div>
      <div className="onboarding-copy"><h1>Your StudyMate is ready!</h1><p>Here&apos;s what we&apos;ve set up for you</p></div>
      <section className="profile-summary" aria-labelledby="profile-summary-title"><h2 id="profile-summary-title">Your profile</h2><div className="profile-chips"><span className="profile-chip profile-chip-blue">{profile.educationBackground?.name}</span><span className="profile-chip profile-chip-purple">{profile.course?.name}</span><span className="profile-chip profile-chip-teal">{profile.academicLevel?.name}</span>{profile.interests.map((interest, index) => <span key={interest.id} className={`profile-chip profile-chip-accent-${index % 3}`}>{interest.name}</span>)}</div></section>
      <section className="recommendations" aria-labelledby="recommendations-title"><h2 id="recommendations-title">Personalized for you</h2><div className="recommendation-grid">{recommendations.map((recommendation) => <RecommendationCard key={recommendation.topic} recommendation={recommendation} />)}</div></section>
      {submissionError ? <p className="selection-count" role="alert">{submissionError.status === 401 ? 'Your session has expired. Please sign in again.' : getApiErrorMessage(submissionError)}</p> : null}
      <Navigation onBack={() => setStep(3)} onNext={finish} final loading={isSubmitting} nextDisabled={!profile.educationBackground || !profile.course || !profile.academicLevel || !profile.interests.length} />
    </section>,
  }

  return <main className="onboarding-page"><div className="onboarding-shell"><OnboardingHeader step={step} />{stepContent[step]}</div></main>
}

export default Onboarding

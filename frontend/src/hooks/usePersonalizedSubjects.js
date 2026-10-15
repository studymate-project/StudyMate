import { useEffect, useMemo, useState } from 'react'
import { listSubjectRecommendations } from '../api/resources'
import { useAuth } from '../auth/useAuth'

const EMPTY_INTERESTS = []
const SUBJECT_COLORS = [
  'bg-[var(--color-primary-soft)]',
  'bg-[var(--color-teal-soft)]',
  'bg-[var(--color-purple-soft)]',
]
const SUBJECT_ICONS = {
  'ai-ml': 'BrainCircuit',
  dbms: 'Database',
  dsa: 'BarChart3',
  java: 'Coffee',
  networks: 'Globe2',
  os: 'Settings',
  python: 'ScrollText',
  react: 'Monitor',
  'web-development': 'Monitor',
}

function normalizeSubject(subject, index) {
  const isTrending = Boolean(subject.is_trending)
  return {
    ...subject,
    colorClass: SUBJECT_COLORS[index % SUBJECT_COLORS.length],
    icon: SUBJECT_ICONS[subject.slug] || 'BookOpen',
    isTrending,
    meta: isTrending
      ? `Trending - ${subject.recent_engagement_count} recent engagements`
      : subject.is_personalized
        ? 'Recommended for your profile'
        : 'Available on StudyMate',
  }
}

export default function usePersonalizedSubjects() {
  const { status: authStatus, user } = useAuth()
  const profile = user?.profile || null
  const profileKey = JSON.stringify({
    onboarding: profile?.onboarding_completed || false,
    background: profile?.education_background || null,
    course: profile?.course || null,
    level: profile?.academic_level || null,
    interests: (profile?.interests || EMPTY_INTERESTS).map((interest) => interest.id || interest.slug || interest.name),
  })
  const requestKey = `${authStatus}:${profileKey}`
  const [state, setState] = useState({ requestKey: null, data: [], error: null, profileComplete: false, hasInterests: false })

  useEffect(() => {
    if (authStatus !== 'authenticated') return undefined

    let active = true
    listSubjectRecommendations().then((data) => {
      if (active) setState({
        requestKey,
        data: (data.results || []).map(normalizeSubject),
        error: null,
        profileComplete: Boolean(data.profile_complete),
        hasInterests: Boolean(data.has_interests),
      })
    }).catch((error) => {
      if (active) setState({ requestKey, data: [], error, profileComplete: false, hasInterests: false })
    })

    return () => {
      active = false
    }
  }, [authStatus, requestKey])

  const currentState = state.requestKey === requestKey ? state : { data: [], error: null, profileComplete: false, hasInterests: false }
  const subjects = useMemo(() => currentState.data, [currentState.data])

  return {
    authStatus,
    error: currentState.error,
    hasSelectedInterests: currentState.hasInterests,
    isProfileComplete: currentState.profileComplete || profile?.onboarding_completed === true,
    loading: authStatus === 'loading' || (authStatus === 'authenticated' && state.requestKey !== requestKey),
    subjects,
  }
}

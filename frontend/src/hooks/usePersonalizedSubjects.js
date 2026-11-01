import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchSubjectRecommendations } from '../api/resources'
import { useAuth } from '../auth/useAuth'
import { QUERY_STALE_TIMES } from '../query/queryClient'
import { subjectKeys } from '../query/queryKeys'

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
  const subjectScope = `${user?.id || 'current'}:${profileKey}`
  const query = useQuery({
    queryKey: subjectKeys.recommendations(subjectScope, 12),
    queryFn: () => fetchSubjectRecommendations(12),
    enabled: authStatus === 'authenticated',
    staleTime: QUERY_STALE_TIMES.subjects,
  })
  const currentData = query.data || {}
  const subjects = useMemo(() => (currentData.results || []).map(normalizeSubject), [currentData.results])

  return {
    authStatus,
    error: query.error,
    hasSelectedInterests: Boolean(currentData.has_interests),
    isProfileComplete: Boolean(currentData.profile_complete) || profile?.onboarding_completed === true,
    loading: authStatus === 'loading' || (authStatus === 'authenticated' && query.isPending),
    subjects,
  }
}

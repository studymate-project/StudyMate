import { getCurrentUser } from './auth'
import { apiClient } from './client'
import { listResources, listSavedResources } from './resources'
import { listAnswers, listQuestions } from './questions'

let currentProfileRequest

function getDisplayName(user, profile) {
  return profile.display_name?.trim()
    || [user.first_name, user.last_name].filter(Boolean).join(' ').trim()
    || user.username
    || 'StudyMate member'
}

function getInitials(name) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')

  return initials.toUpperCase() || 'SM'
}

function normalizeStats(contributionPoints, activity) {
  const stats = [
    { value: activity.resources.length, label: 'Resources Shared' },
    { value: activity.questions.length, label: 'Questions' },
    { value: activity.answers.length, label: 'Answers' },
  ]
  if (contributionPoints !== null && contributionPoints !== undefined) {
    stats.push({ value: contributionPoints, label: 'Contribution Points' })
  }
  return stats
}

export function normalizeProfileResponse(data, activity = {}) {
  const user = data?.user || {}
  const profile = user.profile || {}
  const name = getDisplayName(user, profile)
  const normalizedActivity = {
    resources: activity.resources || [],
    questions: activity.questions || [],
    answers: activity.answers || [],
    savedResources: activity.savedResources || [],
  }

  return {
    user: {
      id: user.id,
      username: user.username,
      name,
      avatarUrl: profile.avatar_url || null,
      // The current API returns foreign-key IDs without catalog details.
      educationBackgroundId: profile.education_background ?? null,
      courseId: profile.course ?? null,
      academicLevelId: profile.academic_level ?? null,
      course: null,
      semester: null,
    },
    profile: {
      initials: getInitials(name),
      displayName: profile.display_name || '',
      bio: profile.bio || '',
      avatarUrl: profile.avatar_url || '',
      college: profile.college || '',
      educationBackgroundId: profile.education_background ?? null,
      courseId: profile.course ?? null,
      academicLevelId: profile.academic_level ?? null,
      tags: [],
      interests: [],
      stats: normalizeStats(profile.contribution_points, normalizedActivity),
      achievements: [],
      resources: normalizedActivity.resources,
      recentQuestions: normalizedActivity.questions.map((question) => ({
        questionId: question.id,
        slug: question.slug,
        title: question.title,
        votes: question.upvotes ?? 0,
        answers: question.answerCount ?? 0,
      })),
      recentAnswers: normalizedActivity.answers,
      savedResources: normalizedActivity.savedResources,
      isFollowing: Boolean(profile.is_following),
    },
  }
}

export async function getCurrentProfile() {
  if (currentProfileRequest) return currentProfileRequest

  currentProfileRequest = getCurrentUser().then(async (user) => {
    const [resourceResult, questionResult, savedResult] = await Promise.all([
      listResources({ page_size: 100 }),
      listQuestions({ page_size: 100 }),
      listSavedResources(),
    ])
    const resources = resourceResult.resources.filter((resource) => resource.authorId === user.id)
    const questions = questionResult.questions.filter((question) => question.author?.id === user.id)
    const answerRequests = questionResult.questions
      .filter((question) => question.answerCount > 0)
      .map((question) => listAnswers(question.id).then(({ answers }) => answers
        .filter((answer) => answer.author?.id === user.id)
        .map((answer) => ({
          ...answer,
          questionTitle: question.title,
          questionSlug: question.slug,
        }))))
    const answerResults = await Promise.allSettled(answerRequests)
    const answers = answerResults
      .filter((result) => result.status === 'fulfilled')
      .flatMap((result) => result.value)

    return normalizeProfileResponse(
      { user },
      { resources, questions, answers, savedResources: savedResult.resources },
    )
  })

  currentProfileRequest.then(
    () => { currentProfileRequest = undefined },
    () => { currentProfileRequest = undefined },
  )

  return currentProfileRequest
}

export function getPublicProfile(username) {
  const normalizedUsername = username?.trim()
  if (!normalizedUsername) return Promise.reject(new Error('A username is required.'))

  return apiClient
    .get(`/users/${encodeURIComponent(normalizedUsername)}/`)
    .then((response) => {
      const data = response.data || {}
      // Public profile responses are returned as StudentProfile records. Keep
      // this tolerant of the wrapped shape used by auth responses as well so
      // profile links remain valid when the API response is reused.
      const profileData = data.profile || data
      const user = data.user || profileData.user || {}
      const name = profileData.display_name?.trim()
        || [user.first_name, user.last_name].filter(Boolean).join(' ').trim()
        || user.username
        || 'StudyMate member'

      return {
        user: {
          id: user.id,
          username: user.username,
          name,
          avatarUrl: profileData.avatar_url || null,
          isFollowing: Boolean(profileData.is_following),
          course: null,
          semester: null,
        },
        profile: {
          bio: profileData.bio || '',
          college: profileData.college || '',
          contributionPoints: profileData.contribution_points ?? 0,
          isFollowing: Boolean(profileData.is_following),
        },
      }
    })
}

export function updateProfile(username, payload) {
  return apiClient
    .patch(`/users/${encodeURIComponent(username)}/`, payload)
    .then((response) => response.data)
}

export function followProfile(username) {
  return apiClient
    .post(`/users/${encodeURIComponent(username)}/follow/`)
    .then((response) => response.data)
}

export function unfollowProfile(username) {
  return apiClient
    .delete(`/users/${encodeURIComponent(username)}/follow/`)
    .then((response) => response.data)
}

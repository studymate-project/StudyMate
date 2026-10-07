import { getCurrentUser } from './auth'
import { apiClient } from './client'
import { listAcademicLevels, listCourses, listEducationBackgrounds } from './onboarding'
import { listResources, listSavedResources } from './resources'
import { listAnswersByAuthor, listQuestions } from './questions'

let currentProfileRequest
const currentProfileCache = new Map()
const CURRENT_PROFILE_CACHE_TTL_MS = 30 * 1000

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

function sameId(first, second) {
  return String(first) === String(second)
}

async function getEducationSelection(profile = {}) {
  if (!profile.education_background) {
    return { background: null, course: null, academicLevel: null }
  }

  const backgrounds = await listEducationBackgrounds()
  const background = backgrounds.find((item) => sameId(item.id, profile.education_background)) || null
  if (!background || !profile.course) {
    return { background, course: null, academicLevel: null }
  }

  const courses = await listCourses(background.id)
  const course = courses.find((item) => sameId(item.id, profile.course)) || null
  if (!course || !profile.academic_level) {
    return { background, course, academicLevel: null }
  }

  const levels = await listAcademicLevels(course.id, background.id)
  return {
    background,
    course,
    academicLevel: levels.find((item) => sameId(item.id, profile.academic_level)) || null,
  }
}

export function normalizeProfileResponse(data, activity = {}, education = {}) {
  const user = data?.user || {}
  const profile = user.profile || {}
  const background = education.background || null
  const course = education.course || null
  const academicLevel = education.academicLevel || null
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
      educationBackgroundId: profile.education_background ?? null,
      courseId: profile.course ?? null,
      academicLevelId: profile.academic_level ?? null,
      course: course?.name || profile.custom_course || null,
      semester: academicLevel?.name || profile.academic_level_value || null,
    },
    profile: {
      initials: getInitials(name),
      displayName: profile.display_name || '',
      bio: profile.bio || '',
      avatarUrl: profile.avatar_url || '',
      college: profile.college || '',
      country: profile.country || '',
      state: profile.state || '',
      city: profile.city || '',
      educationBackground: background,
      educationBackgroundId: profile.education_background ?? null,
      customBackground: profile.custom_background || '',
      course,
      courseId: profile.course ?? null,
      customCourse: profile.custom_course || '',
      academicLevel,
      academicLevelId: profile.academic_level ?? null,
      academicLevelType: profile.academic_level_type || academicLevel?.level_type || '',
      academicLevelValue: profile.academic_level_value || academicLevel?.name || '',
      tags: [],
      interests: profile.interests || [],
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

export async function getCurrentProfile(userOverride = null) {
  const knownUser = userOverride || null
  const cacheKey = knownUser?.id ? String(knownUser.id) : null
  const cached = cacheKey ? currentProfileCache.get(cacheKey) : null
  if (cached && cached.expiresAt > Date.now()) return cached.data
  if (currentProfileRequest) return currentProfileRequest

  currentProfileRequest = Promise.resolve(userOverride || getCurrentUser()).then(async (user) => {
    const [education, resourceResult, questionResult, savedResult] = await Promise.all([
      getEducationSelection(user.profile),
      listResources({ uploader: user.id, page_size: 20 }),
      listQuestions({ author: user.id, page_size: 20 }),
      listSavedResources(),
    ])
    const resources = resourceResult.resources.filter((resource) => resource.authorId === user.id)
    const questions = questionResult.questions.filter((question) => question.author?.id === user.id)
    const { answers } = await listAnswersByAuthor()

    const data = normalizeProfileResponse(
      { user },
      { resources, questions, answers, savedResources: savedResult.resources },
      education,
    )
    currentProfileCache.set(String(user.id), { data, expiresAt: Date.now() + CURRENT_PROFILE_CACHE_TTL_MS })
    return data
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
    .then(async (response) => {
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

      const education = await getEducationSelection(profileData)
      return {
        user: {
          id: user.id,
          username: user.username,
          name,
          avatarUrl: profileData.avatar_url || null,
          isFollowing: Boolean(profileData.is_following),
          course: education.course?.name || profileData.custom_course || null,
          semester: education.academicLevel?.name || profileData.academic_level_value || null,
        },
        profile: {
          bio: profileData.bio || '',
          college: profileData.college || '',
          country: profileData.country || '',
          state: profileData.state || '',
          city: profileData.city || '',
          educationBackground: education.background,
          educationBackgroundId: profileData.education_background ?? null,
          customBackground: profileData.custom_background || '',
          course: education.course,
          courseId: profileData.course ?? null,
          customCourse: profileData.custom_course || '',
          academicLevel: education.academicLevel,
          academicLevelId: profileData.academic_level ?? null,
          academicLevelType: profileData.academic_level_type || education.academicLevel?.level_type || '',
          academicLevelValue: profileData.academic_level_value || education.academicLevel?.name || '',
          contributionPoints: profileData.contribution_points ?? 0,
          isFollowing: Boolean(profileData.is_following),
        },
      }
    })
}

export function updateProfile(username, payload) {
  return apiClient
    .patch(`/users/${encodeURIComponent(username)}/`, payload)
    .then((response) => {
      currentProfileCache.clear()
      return response.data
    })
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

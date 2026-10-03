import { apiClient } from './client'

function getResults(data) {
  if (Array.isArray(data)) return data
  return Array.isArray(data?.results) ? data.results : []
}

async function listCatalog(path, params) {
  const response = await apiClient.get(path, { params })
  return getResults(response.data)
}

export function listEducationBackgrounds() {
  return listCatalog('/education/backgrounds/')
}

export function listCourses(backgroundId) {
  return listCatalog('/education/courses/', { background: backgroundId })
}

export function listAcademicLevels(courseId) {
  return listCatalog('/education/levels/', { course: courseId })
}

export function listInterests(courseId) {
  return listCatalog('/education/interests/', { course: courseId })
}

export async function submitOnboarding(payload) {
  const response = await apiClient.post('/users/onboarding/', payload)
  return response.data
}

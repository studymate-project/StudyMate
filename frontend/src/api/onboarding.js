import { apiClient } from './client'

export const ACADEMIC_STAGE_TYPES = [
  { value: 'class', label: 'Class' },
  { value: 'semester', label: 'Semester' },
  { value: 'year', label: 'Year' },
  { value: 'level', label: 'Level' },
  { value: 'stage', label: 'Stage' },
  { value: 'other', label: 'Other' },
]

const CATALOG_CACHE_TTL_MS = 5 * 60 * 1000
const catalogCache = new Map()
const catalogRequests = new Map()

function getResults(data) {
  if (Array.isArray(data)) return data
  return Array.isArray(data?.results) ? data.results : []
}

async function listCatalog(path, params) {
  const key = `${path}?${JSON.stringify(params || {})}`
  const cached = catalogCache.get(key)
  if (cached && cached.expiresAt > Date.now()) return cached.data

  const existingRequest = catalogRequests.get(key)
  if (existingRequest) return existingRequest

  const request = apiClient.get(path, { params }).then((response) => {
    const data = getResults(response.data)
    catalogCache.set(key, { data, expiresAt: Date.now() + CATALOG_CACHE_TTL_MS })
    return data
  }).finally(() => {
    catalogRequests.delete(key)
  })
  catalogRequests.set(key, request)
  return request
}

export function clearEducationCatalogCache() {
  catalogCache.clear()
}

export function listEducationBackgrounds() {
  return listCatalog('/education/backgrounds/')
}

export function listCourses(backgroundId) {
  return listCatalog('/education/courses/', { background: backgroundId })
}

export function listAcademicLevels(courseId, backgroundId) {
  return listCatalog('/education/levels/', {
    course: courseId,
    ...(backgroundId ? { background: backgroundId } : {}),
  })
}

export function listInterests(courseId) {
  return listCatalog('/education/interests/', { course: courseId })
}

export async function submitOnboarding(payload) {
  const response = await apiClient.post('/users/onboarding/', payload)
  return response.data
}

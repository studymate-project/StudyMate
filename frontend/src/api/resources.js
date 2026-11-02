import { apiClient } from './client.js'
import { queryClient, QUERY_STALE_TIMES } from '../query/queryClient.js'
import { resourceKeys } from '../query/queryKeys.js'

const resourceTypeLabels = {
  file: 'File',
  video: 'Video',
  notes: 'Notes',
  pdf: 'PDF',
  cheat_sheet: 'Cheat Sheet',
  presentation: 'Presentation',
  assignment: 'Assignment',
  question_paper: 'Question Paper',
  study_guide: 'Study Guide',
  link: 'Link',
  other: 'Other',
}

const choiceLabels = {
  beginner: 'Beginner',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
}

const colorClasses = [
  'bg-[var(--color-primary-soft)]',
  'bg-[var(--color-teal-soft)]',
  'bg-[var(--color-purple-soft)]',
  'bg-[var(--color-primary-soft)]',
  'bg-[var(--color-teal-soft)]',
  'bg-[var(--color-purple-soft)]',
  'bg-[var(--color-primary-soft)]',
]

const supportedQueryKeys = new Set([
  'page',
  'page_size',
  'search',
  'subject',
  'topic',
  'resource_type',
  'academic_level',
  'difficulty',
  'tags',
  'ordering',
  'uploader',
])

const resourceRequests = new Map()
const savedResourceRequests = new Map()

function formatDate(value) {
  if (!value) return null

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null

  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

function formatAuthor(uploader) {
  if (!uploader) return null

  const name = [uploader.first_name, uploader.last_name].filter(Boolean).join(' ')
  return {
    id: uploader.id,
    username: uploader.username,
    avatarUrl: uploader.avatar_url || null,
    name: name || uploader.username || 'StudyMate member',
  }
}

function getColorClass(id) {
  const numericId = Number(id)
  const index = Number.isFinite(numericId) ? numericId % colorClasses.length : 0
  return colorClasses[index]
}

export function normalizeResource(resource) {
  const author = formatAuthor(resource.uploader)

  return {
    id: resource.id,
    targetType: 'resource',
    slug: resource.slug,
    title: resource.title,
    type: resourceTypeLabels[resource.resource_type] || resource.resource_type,
    resourceType: resource.resource_type,
    subject: resource.subject,
    topic: resource.topic,
    course: resource.course || '',
    semester: resource.semester || '',
    authorId: author?.id,
    author,
    academicLevel: resource.academic_level ?? null,
    rating: resource.rating ?? null,
    ratingCount: resource.rating_count ?? 0,
    userRating: resource.user_rating ?? null,
    views: resource.views ?? null,
    downloads: resource.downloads ?? null,
    saves: resource.saves ?? null,
    upvotes: resource.upvotes ?? null,
    isSaved: Boolean(resource.is_saved),
    difficulty: choiceLabels[resource.difficulty] || resource.difficulty || null,
    createdAt: resource.created_at || null,
    uploadedAt: formatDate(resource.created_at),
    description: resource.description,
    resourceUrl: resource.file || resource.external_url || null,
    tags: Array.isArray(resource.tags) ? resource.tags.map((tag) => tag.name).filter(Boolean) : [],
    colorClass: getColorClass(resource.id),
  }
}

function normalizeParams(params) {
  return Object.fromEntries(
    Object.entries(params).filter(([key, value]) => (
      supportedQueryKeys.has(key)
      && value !== undefined
      && value !== null
      && value !== ''
      && !(Array.isArray(value) && value.length === 0)
    )),
  )
}

function normalizeResponse(data) {
  const results = Array.isArray(data) ? data : data?.results || []

  return {
    resources: results.map(normalizeResource),
    pagination: {
      count: Array.isArray(data) ? results.length : data?.count || 0,
      next: Array.isArray(data) ? null : data?.next || null,
      previous: Array.isArray(data) ? null : data?.previous || null,
    },
  }
}

export function fetchResourceList(params = {}) {
  const query = normalizeParams(params)
  return apiClient
    .get('/resources/', {
      params: query,
      paramsSerializer: { indexes: null },
    })
    .then((response) => normalizeResponse(response.data))
}

export function listResources(params = {}) {
  const query = normalizeParams(params)
  const requestKey = JSON.stringify(query)
  const existingRequest = resourceRequests.get(requestKey)
  if (existingRequest) return existingRequest

  const request = queryClient.fetchQuery({
    queryKey: resourceKeys.list(query),
    queryFn: () => fetchResourceList(query),
    staleTime: QUERY_STALE_TIMES.lists,
  })
  resourceRequests.set(requestKey, request)
  request.then(
    () => { if (resourceRequests.get(requestKey) === request) resourceRequests.delete(requestKey) },
    () => { if (resourceRequests.get(requestKey) === request) resourceRequests.delete(requestKey) },
  )
  return request
}

export function clearResourceListCache() {
  resourceRequests.clear()
  savedResourceRequests.clear()
  queryClient.invalidateQueries({ queryKey: resourceKeys.lists(), refetchType: 'active' })
  queryClient.invalidateQueries({ queryKey: resourceKeys.savedLists(), refetchType: 'active' })
  queryClient.invalidateQueries({ queryKey: resourceKeys.details() })
}

export function createResource(formData, uploadId) {
  return apiClient
    .post('/resources/', formData, {
      timeout: 120000,
      headers: uploadId ? { 'X-Upload-ID': uploadId } : undefined,
    })
    .then((response) => {
      clearResourceListCache()
      return response.data
    })
}

export function fetchSavedResourceList(params = {}) {
  const query = normalizeParams(params)
  return apiClient.get('/saved-resources/', { params: query }).then((response) => normalizeResponse(response.data))
}

export function listSavedResources(params = {}) {
  const query = normalizeParams(params)
  const requestKey = JSON.stringify(query)
  const existingRequest = savedResourceRequests.get(requestKey)
  if (existingRequest) return existingRequest

  const request = queryClient.fetchQuery({
    queryKey: resourceKeys.savedList(query),
    queryFn: () => fetchSavedResourceList(query),
    staleTime: QUERY_STALE_TIMES.lists,
  })
  savedResourceRequests.set(requestKey, request)
  request.then(
    () => { if (savedResourceRequests.get(requestKey) === request) savedResourceRequests.delete(requestKey) },
    () => { if (savedResourceRequests.get(requestKey) === request) savedResourceRequests.delete(requestKey) },
  )
  return request
}

async function listAllPages(listPage, params = {}) {
  const resources = []
  let page = 1
  let pagination

  while (true) {
    const result = await listPage({ ...params, page, page_size: 100 })
    resources.push(...result.resources)
    pagination = result.pagination
    if (!pagination.next) break
    page += 1
  }

  return { resources, pagination: { ...pagination, count: pagination.count || resources.length, next: null, previous: null } }
}

export function listAllResources(params = {}) {
  return listAllPages(listResources, params)
}

export function listAllSavedResources(params = {}) {
  return listAllPages(listSavedResources, params)
}

export function saveResource(resourceId) {
  return apiClient.post(`/resources/${resourceId}/save/`).then((response) => {
    clearResourceListCache()
    return response.data
  })
}

export function unsaveResource(resourceId) {
  return apiClient.delete(`/resources/${resourceId}/save/`).then((response) => {
    clearResourceListCache()
    return response.data
  })
}

export function deleteResource(resourceId) {
  return apiClient.delete(`/resources/${resourceId}/`).then((response) => {
    clearResourceListCache()
    return response.data
  })
}

export function fetchResourceDetail(slug) {
  return apiClient
    .get(`/resources/${encodeURIComponent(slug)}/`)
    .then((response) => normalizeResource(response.data))
}

export function getResourceBySlug(slug) {
  const normalizedSlug = slug?.trim()
  if (!normalizedSlug) return Promise.reject(new Error('A resource slug is required.'))

  return queryClient.fetchQuery({
    queryKey: resourceKeys.detail(normalizedSlug),
    queryFn: () => fetchResourceDetail(normalizedSlug),
    staleTime: QUERY_STALE_TIMES.details,
  })
}

export function trackResourceDownload(resourceId) {
  return apiClient.post(`/resources/${resourceId}/download/`).then((response) => response.data)
}

export function trackResourceView(resourceId) {
  return apiClient.post(`/resources/${resourceId}/view/`).then((response) => response.data)
}

export function saveResourceRating(resourceId, rating) {
  return apiClient.post(`/resources/${resourceId}/rating/`, { rating }).then((response) => {
    clearResourceListCache()
    return response.data
  })
}

export function deleteResourceRating(resourceId) {
  return apiClient.delete(`/resources/${resourceId}/rating/`).then((response) => {
    clearResourceListCache()
    return response.data
  })
}

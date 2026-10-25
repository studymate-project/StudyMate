import { apiClient } from './client.js'
import { isValidYouTubeVideoId } from '../utils/youtubeUtils.js'

const choiceLabels = {
  beginner: 'Beginner',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
}

const inFlightRequests = new Map()
const supportedQueryKeys = new Set([
  'page',
  'page_size',
  'search',
  'subject',
  'topic',
  'academic_level',
  'difficulty',
  'tags',
  'ordering',
  'uploader',
])

function normalizeParams(params) {
  return Object.fromEntries(
    Object.entries(params || {}).filter(([key, value]) => (
      supportedQueryKeys.has(key)
      && value !== undefined
      && value !== null
      && value !== ''
      && !(Array.isArray(value) && value.length === 0)
    )).sort(([firstKey], [secondKey]) => firstKey.localeCompare(secondKey)),
  )
}

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

function normalizeUploader(uploader) {
  if (!uploader) return null

  const name = [uploader.first_name, uploader.last_name].filter(Boolean).join(' ')
  return {
    id: uploader.id,
    username: uploader.username,
    name: name || uploader.username || 'StudyMate member',
  }
}

export function normalizeVideo(video) {
  const youtubeVideoId = isValidYouTubeVideoId(video.youtube_video_id)
    ? video.youtube_video_id
    : null

  return {
    id: video.id,
    targetType: 'video',
    slug: video.slug,
    title: video.title,
    description: video.description,
    subject: video.subject,
    topic: video.topic,
    course: video.course || '',
    semester: video.semester || '',
    academicLevel: video.academic_level ?? null,
    difficulty: choiceLabels[video.difficulty] || video.difficulty || null,
    tags: Array.isArray(video.tags) ? video.tags.map((tag) => tag.name).filter(Boolean) : [],
    author: normalizeUploader(video.uploader),
    createdAt: video.created_at || null,
    uploadedAt: formatDate(video.created_at),
    youtubeVideoId,
    originalUrl: video.original_url || null,
    thumbnailUrl: video.thumbnail_url || null,
    durationSeconds: video.duration_seconds ?? null,
    rating: video.rating ?? null,
    ratingCount: video.rating_count ?? 0,
    userRating: video.user_rating ?? null,
    views: video.views ?? null,
    upvotes: video.upvotes ?? null,
  }
}

export function deleteVideo(videoSlug) {
  const normalizedSlug = videoSlug?.trim()
  if (!normalizedSlug) return Promise.reject(new Error('A video slug is required.'))

  return apiClient.delete(`/videos/${encodeURIComponent(normalizedSlug)}/`).then((response) => {
    clearVideoListCache()
    return response.data
  })
}

export function createVideo(payload) {
  return apiClient.post('/videos/', payload).then((response) => {
    clearVideoListCache()
    return normalizeVideo(response.data)
  })
}

export function listVideos(params = {}) {
  const query = normalizeParams(params)
  const requestKey = `video-list:${JSON.stringify(query)}`
  // The API includes the authenticated user's own non-published videos, so
  // only coalesce concurrent requests; do not retain a completed list across
  // account changes or logout/login transitions.
  const existingRequest = inFlightRequests.get(requestKey)
  if (existingRequest) return existingRequest

  const request = apiClient.get('/videos/', { params: query }).then((response) => {
    const data = response.data
    const results = Array.isArray(data) ? data : data?.results || []

    const normalized = {
      videos: results.map(normalizeVideo),
      pagination: {
        count: Array.isArray(data) ? results.length : data?.count || 0,
        next: Array.isArray(data) ? null : data?.next || null,
        previous: Array.isArray(data) ? null : data?.previous || null,
      },
    }
    return normalized
  })

  inFlightRequests.set(requestKey, request)
  request.then(
    () => { if (inFlightRequests.get(requestKey) === request) inFlightRequests.delete(requestKey) },
    () => { if (inFlightRequests.get(requestKey) === request) inFlightRequests.delete(requestKey) },
  )
  return request
}

export async function listAllVideos(params = {}) {
  const videos = []
  let page = 1
  let pagination

  while (true) {
    const result = await listVideos({ ...params, page, page_size: 100 })
    videos.push(...result.videos)
    pagination = result.pagination
    if (!pagination.next) break
    page += 1
  }

  return { videos, pagination: { ...pagination, count: pagination.count || videos.length, next: null, previous: null } }
}

export function clearVideoListCache() {
  inFlightRequests.forEach((request, key) => {
    if (String(key).startsWith('video-list:')) inFlightRequests.delete(key)
  })
}

export function getVideoBySlug(slug) {
  const normalizedSlug = slug?.trim()
  if (!normalizedSlug) return Promise.reject(new Error('A video slug is required.'))

  const requestKey = `video-detail:${normalizedSlug}`
  const existingRequest = inFlightRequests.get(requestKey)
  if (existingRequest) return existingRequest

  const request = apiClient
    .get(`/videos/${encodeURIComponent(normalizedSlug)}/`)
    .then((response) => normalizeVideo(response.data))

  inFlightRequests.set(requestKey, request)
  request.then(
    () => inFlightRequests.delete(requestKey),
    () => inFlightRequests.delete(requestKey),
  )

  return request
}

export function saveVideoRating(videoSlug, rating) {
  return apiClient.post(`/videos/${encodeURIComponent(videoSlug)}/rating/`, { rating }).then((response) => {
    clearVideoListCache()
    return response.data
  })
}

export function deleteVideoRating(videoSlug) {
  return apiClient.delete(`/videos/${encodeURIComponent(videoSlug)}/rating/`).then((response) => {
    clearVideoListCache()
    return response.data
  })
}

import { apiClient } from './client'
import { isValidYouTubeVideoId } from '../utils/youtubeUtils'

const choiceLabels = {
  beginner: 'Beginner',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
}

const inFlightRequests = new Map()

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

export function createVideo(payload) {
  return apiClient.post('/videos/', payload).then((response) => normalizeVideo(response.data))
}

export function listVideos(params = {}) {
  return apiClient.get('/videos/', { params }).then((response) => {
    const data = response.data
    const results = Array.isArray(data) ? data : data?.results || []

    return {
      videos: results.map(normalizeVideo),
      pagination: {
        count: Array.isArray(data) ? results.length : data?.count || 0,
        next: Array.isArray(data) ? null : data?.next || null,
        previous: Array.isArray(data) ? null : data?.previous || null,
      },
    }
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
  return apiClient.post(`/videos/${encodeURIComponent(videoSlug)}/rating/`, { rating }).then((response) => response.data)
}

export function deleteVideoRating(videoSlug) {
  return apiClient.delete(`/videos/${encodeURIComponent(videoSlug)}/rating/`).then((response) => response.data)
}

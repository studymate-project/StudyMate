import { apiClient } from './client'

function formatDate(value) {
  if (!value) return 'Date unavailable'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Date unavailable'
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

function normalizeAuthor(author) {
  if (!author) return null
  const name = [author.first_name, author.last_name].filter(Boolean).join(' ')
  return {
    id: author.id,
    username: author.username,
    name: name || author.username || 'StudyMate member',
  }
}

function normalizeReply(reply) {
  return {
    id: reply.id,
    parentId: reply.parent,
    author: normalizeAuthor(reply.author),
    body: reply.body,
    likeCount: reply.like_count ?? 0,
    liked: Boolean(reply.liked),
    createdAt: formatDate(reply.created_at),
  }
}

function normalizeComment(comment) {
  return {
    id: comment.id,
    parentId: comment.parent,
    author: normalizeAuthor(comment.author),
    body: comment.body,
    likeCount: comment.like_count ?? 0,
    liked: Boolean(comment.liked),
    createdAt: formatDate(comment.created_at),
    replies: Array.isArray(comment.replies) ? comment.replies.map(normalizeReply) : [],
  }
}

function discussionPath(targetType, target) {
  if (targetType === 'resource') return `/discussion/resources/${encodeURIComponent(target)}/`
  return `/discussion/videos/${encodeURIComponent(target)}/`
}

async function listDiscussion(targetType, target) {
  const comments = []
  let page = 1
  let hasNextPage = true

  while (hasNextPage) {
    const response = await apiClient.get(discussionPath(targetType, target), {
      params: { page, page_size: 100 },
    })
    const data = response.data
    const results = Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : []
    comments.push(...results.map(normalizeComment))
    hasNextPage = !Array.isArray(data) && Boolean(data?.next)
    page += 1
  }

  return comments
}

export function listResourceDiscussion(resourceId) {
  return listDiscussion('resource', resourceId)
}

export function listVideoDiscussion(videoSlug) {
  return listDiscussion('video', videoSlug)
}

function createDiscussionComment(targetType, target, body, parent = null) {
  const payload = { body }
  if (parent !== null && parent !== undefined) payload.parent = parent
  return apiClient.post(discussionPath(targetType, target), payload).then((response) => normalizeComment(response.data))
}

export function createResourceDiscussionComment(resourceId, body, parent = null) {
  return createDiscussionComment('resource', resourceId, body, parent)
}

export function createVideoDiscussionComment(videoSlug, body, parent = null) {
  return createDiscussionComment('video', videoSlug, body, parent)
}

export function likeDiscussionComment(commentId) {
  return apiClient.post(`/discussion/comments/${encodeURIComponent(commentId)}/like/`).then((response) => response.data)
}

export function unlikeDiscussionComment(commentId) {
  return apiClient.delete(`/discussion/comments/${encodeURIComponent(commentId)}/like/`).then((response) => response.data)
}

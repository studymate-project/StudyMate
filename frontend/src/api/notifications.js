import { apiClient } from './client'

const categoryByNotificationType = {
  question_answered: 'Answers',
  answer_upvoted: 'Upvotes',
  resource_upvoted: 'Upvotes',
  resource_saved: 'Resources',
}

const notificationTypeLabels = {
  question_answered: 'Question answered',
  answer_upvoted: 'Answer upvoted',
  resource_upvoted: 'Resource upvoted',
  resource_saved: 'Resource saved',
  new_follower: 'New follower',
  system: 'System notification',
}

const actorColors = ['bg-[var(--color-primary-soft)]', 'bg-[var(--color-teal-soft)]', 'bg-[var(--color-purple-soft)]', 'bg-[var(--color-primary-soft)]', 'bg-[var(--color-teal-soft)]']

let notificationListRequest
let notificationListCache
let notificationCacheGeneration = 0
const NOTIFICATION_CACHE_TTL_MS = 30 * 1000

function getInitials(actor) {
  const name = [actor?.first_name, actor?.last_name].filter(Boolean).join(' ') || actor?.username || ''
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')

  return initials.toUpperCase() || 'SM'
}

function getActorColor(actor) {
  const actorId = Number(actor?.id)
  const index = Number.isFinite(actorId) ? actorId % actorColors.length : 0
  return actorColors[index]
}

function formatRelativeTime(value) {
  if (!value) return ''

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''

  const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000))
  if (seconds < 60) return 'Just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`
  if (hours < 48) return 'Yesterday'
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} days ago`

  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(date)
}

function getGroup(value) {
  if (!value) return 'Earlier'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Earlier'

  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const startOfNotificationDay = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const dayDifference = Math.floor((startOfToday - startOfNotificationDay) / 86400000)

  if (dayDifference === 0) return 'Today'
  if (dayDifference === 1) return 'Yesterday'
  return 'Earlier'
}

function getInternalTarget(notification, actor) {
  const payloadTarget = notification.payload?.target || notification.payload?.url
  if (typeof payloadTarget === 'string' && payloadTarget.startsWith('/')) return payloadTarget

  if (notification.notification_type === 'new_follower' && actor?.username) {
    return `/users/${encodeURIComponent(actor.username)}`
  }

  return null
}

export function normalizeNotification(notification) {
  const actor = notification.actor || null
  const typeLabel = notificationTypeLabels[notification.notification_type] || notification.notification_type || 'Notification'

  return {
    id: notification.id,
    notificationType: notification.notification_type,
    type: categoryByNotificationType[notification.notification_type] || 'Other',
    actor: {
      id: actor?.id,
      username: actor?.username,
      initials: getInitials(actor),
      color: getActorColor(actor),
    },
    message: notification.message || typeLabel,
    time: formatRelativeTime(notification.created_at),
    group: getGroup(notification.created_at),
    unread: !notification.is_read,
    target: getInternalTarget(notification, actor),
    contentType: notification.content_type,
    objectId: notification.object_id,
    payload: notification.payload || {},
  }
}

function normalizeResponse(data) {
  const results = Array.isArray(data) ? data : data?.results || []

  return {
    notifications: results.map(normalizeNotification),
    pagination: {
      count: Array.isArray(data) ? results.length : data?.count || 0,
      next: Array.isArray(data) ? null : data?.next || null,
      previous: Array.isArray(data) ? null : data?.previous || null,
    },
  }
}

export function listNotifications() {
  if (notificationListCache && notificationListCache.expiresAt > Date.now()) {
    return Promise.resolve(notificationListCache.data)
  }
  if (notificationListRequest) return notificationListRequest

  const requestGeneration = notificationCacheGeneration
  const request = apiClient
    .get('/notifications/')
    .then((response) => {
      const data = normalizeResponse(response.data)
      if (requestGeneration === notificationCacheGeneration) {
        notificationListCache = { data, expiresAt: Date.now() + NOTIFICATION_CACHE_TTL_MS }
      }
      return data
    })

  notificationListRequest = request
  request.then(
    () => { if (notificationListRequest === request) notificationListRequest = undefined },
    () => { if (notificationListRequest === request) notificationListRequest = undefined },
  )

  return notificationListRequest
}

export function clearNotificationCache() {
  notificationListCache = undefined
  notificationCacheGeneration += 1
  notificationListRequest = undefined
}

export function markNotificationRead(notificationId) {
  return apiClient
    .patch(`/notifications/${notificationId}/read/`)
    .then((response) => {
      clearNotificationCache()
      return normalizeNotification(response.data)
    })
}

export function markAllNotificationsRead() {
  return apiClient.patch('/notifications/read-all/').then((response) => {
    clearNotificationCache()
    return response.data
  })
}

const categoryByNotificationType = {
  question_answered: 'Answers',
  answer_upvoted: 'Upvotes',
  resource_upvoted: 'Upvotes',
  resource_saved: 'Resources',
}

export function getNotificationCategory(notificationType, target) {
  if (categoryByNotificationType[notificationType]) return categoryByNotificationType[notificationType]
  return ['resource', 'video', 'external'].includes(target?.kind) ? 'Resources' : 'Other'
}

export function matchesNotificationTab(notification, tab) {
  if (tab === 'All') return true
  if (tab === 'Resources') {
    return notification.type === 'Resources' || ['resource', 'video', 'external'].includes(notification.targetKind)
  }
  return notification.type === tab
}

function getSafeInternalTarget(value) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : null
}

function getSafeExternalTarget(value) {
  if (typeof value !== 'string') return null
  try {
    const url = new URL(value)
    if (!['http:', 'https:'].includes(url.protocol) || !url.hostname || url.username || url.password) return null
    return url.toString()
  } catch {
    return null
  }
}

export function getNotificationTarget(notification, actor) {
  const serverTarget = notification.target
  if (serverTarget && typeof serverTarget === 'object') {
    const kind = serverTarget.kind
    const resourceKinds = new Set(['resource', 'video', 'question', 'profile'])
    if (resourceKinds.has(kind)) {
      const url = getSafeInternalTarget(serverTarget.url)
      if (url) return { kind, url, resourceType: serverTarget.resource_type || null }
    }
    if (kind === 'external') {
      const url = getSafeExternalTarget(serverTarget.url)
      if (url) return { kind, url, resourceType: serverTarget.resource_type || 'link' }
    }
  }

  const payloadTarget = notification.payload?.target || notification.payload?.url
  const internalTarget = getSafeInternalTarget(payloadTarget)
  if (internalTarget) return { kind: 'internal', url: internalTarget, resourceType: null }

  if (notification.notification_type === 'new_follower' && actor?.username) {
    return { kind: 'profile', url: `/users/${encodeURIComponent(actor.username)}`, resourceType: null }
  }

  return null
}

export function openNotificationTarget(notification, navigate) {
  if (!notification?.target) return false
  if (notification.targetKind === 'external') {
    window.open(notification.target, '_blank', 'noopener,noreferrer')
    return true
  }
  navigate(notification.target)
  return true
}

export function profileResourceOpenTarget(resource) {
  if (resource.resourceType === 'link' && resource.resourceUrl) return resource.resourceUrl
  if (resource.targetType === 'video') return `/videos/${resource.slug}`
  return `/resources/${resource.slug}`
}

export function confirmProfileResourceDeletion(resource, confirmFn) {
  return confirmFn(`Delete “${resource.title}”? This cannot be undone.`)
}

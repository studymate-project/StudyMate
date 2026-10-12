const frontendRoutePrefixes = {
  resource: '/resources',
  video: '/videos',
  question: '/questions',
}

const apiRouteTypes = {
  resources: 'resource',
  videos: 'video',
  questions: 'question',
}

export function getSearchResultRoute(result) {
  const detailUrl = typeof result?.detail_url === 'string' ? result.detail_url : ''
  const match = detailUrl.match(/^\/api\/(resources|videos|questions)\/([^/?#]+)\/?$/)
  const routeType = match ? apiRouteTypes[match[1]] : null
  if (!routeType || routeType !== result?.type || !frontendRoutePrefixes[routeType]) return null

  let slug
  try {
    slug = decodeURIComponent(match[2])
  } catch {
    return null
  }
  return `${frontendRoutePrefixes[routeType]}/${encodeURIComponent(slug)}`
}

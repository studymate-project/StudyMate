export function getLocationPath(location) {
  const pathname = typeof location?.pathname === 'string' && location.pathname.startsWith('/')
    ? location.pathname
    : '/'
  const search = typeof location?.search === 'string' ? location.search : ''
  const hash = typeof location?.hash === 'string' ? location.hash : ''
  return `${pathname}${search}${hash}`
}

export function getLoginState(location) {
  return { from: getLocationPath(location) }
}

export function getPostAuthDestination(user, from) {
  if (user?.profile?.onboarding_completed !== true) return '/onboarding'
  const fromPath = typeof from === 'string' ? from.split(/[?#]/, 1)[0] : ''
  if (typeof from === 'string' && from.startsWith('/') && !/^\/[\\/]/.test(from) && !['/login', '/signup', '/onboarding'].includes(fromPath)) {
    return from
  }
  return '/home'
}

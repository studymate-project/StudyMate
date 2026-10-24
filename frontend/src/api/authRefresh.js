export const DEFAULT_REFRESH_COOLDOWN_MS = 30_000

function getRetryAfterHeader(error) {
  const headers = error?.response?.headers
  if (!headers) return null
  if (typeof headers.get === 'function') return headers.get('retry-after')
  return headers['retry-after'] ?? headers['Retry-After'] ?? null
}

export function getRetryAfterMs(error, now = Date.now(), fallbackMs = DEFAULT_REFRESH_COOLDOWN_MS) {
  const value = getRetryAfterHeader(error)
  if (value === null || value === undefined || value === '') return fallbackMs

  const seconds = Number(value)
  if (Number.isFinite(seconds) && seconds >= 0) return Math.max(1000, seconds * 1000)

  const retryAt = Date.parse(value)
  if (Number.isFinite(retryAt)) return Math.max(1000, retryAt - now)

  return fallbackMs
}

export function createRefreshCoordinator(refresh, { now = Date.now, fallbackCooldownMs = DEFAULT_REFRESH_COOLDOWN_MS } = {}) {
  let inFlight
  let blockedError
  let blockedUntil = 0
  let permanentlyUnavailable = false

  const request = () => {
    const currentTime = now()
    if (inFlight) return inFlight

    if (permanentlyUnavailable || blockedUntil > currentTime) {
      return Promise.reject(blockedError)
    }

    blockedError = undefined
    blockedUntil = 0
    inFlight = Promise.resolve()
      .then(refresh)
      .then((result) => {
        permanentlyUnavailable = false
        return result
      })
      .catch((error) => {
        blockedError = error
        if (error?.status === 401) {
          permanentlyUnavailable = true
        } else if (error?.status === 429) {
          blockedUntil = now() + getRetryAfterMs(error, now(), fallbackCooldownMs)
        }
        throw error
      })
      .finally(() => {
        inFlight = undefined
      })

    return inFlight
  }

  const reset = () => {
    blockedError = undefined
    blockedUntil = 0
    permanentlyUnavailable = false
  }

  return { request, reset }
}

export function isRefreshEndpoint(config) {
  const path = String(config?.url || '').split('?')[0]
  return path === '/auth/refresh/' || path.endsWith('/auth/refresh/')
}

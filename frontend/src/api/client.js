import axios from 'axios'
import {
  API_BASE_URL,
  API_TIMEOUT_MS,
  CSRF_BOOTSTRAP_PATH,
  CSRF_COOKIE_NAME,
  CSRF_HEADER_NAME,
} from './config.js'
import { normalizeApiError } from './errors.js'
import { createRefreshCoordinator, isRefreshEndpoint } from './authRefresh.js'

const unsafeMethods = new Set(['post', 'put', 'patch', 'delete'])

export function readCookie(name) {
  if (typeof document === 'undefined') return null

  const encodedName = `${encodeURIComponent(name)}=`
  const cookie = document.cookie.split('; ').find((entry) => entry.startsWith(encodedName))
  return cookie ? decodeURIComponent(cookie.slice(encodedName.length)) : null
}

const csrfBootstrapClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  withCredentials: true,
})

let csrfBootstrapRequest
let csrfToken
let authFailureHandler

export function setAuthFailureHandler(handler) {
  authFailureHandler = handler
  return () => {
    if (authFailureHandler === handler) authFailureHandler = undefined
  }
}

function notifyAuthFailure() {
  try {
    authFailureHandler?.()
  } catch {
    // Session invalidation must not change the original API error.
  }
}

async function ensureCsrfCookie({ force = false } = {}) {
  if (force) csrfToken = undefined
  if (csrfToken) return csrfToken

  const existingToken = readCookie(CSRF_COOKIE_NAME)
  if (existingToken) return existingToken

  if (!csrfBootstrapRequest) {
    csrfBootstrapRequest = csrfBootstrapClient
      .get(CSRF_BOOTSTRAP_PATH)
      .then((response) => {
        csrfToken = response.data?.csrf_token || readCookie(CSRF_COOKIE_NAME)
        if (!csrfToken) {
          throw new Error('Unable to initialize secure requests. Please try again.')
        }
        return csrfToken
      })
      .catch((error) => {
        throw normalizeApiError(error)
      })
      .finally(() => {
        csrfBootstrapRequest = undefined
      })
  }

  return csrfBootstrapRequest
}

function isCsrfFailure(error) {
  const detail = error?.response?.data?.detail
  return error?.response?.status === 403
    && typeof detail === 'string'
    && /csrf/i.test(detail)
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  withCredentials: true,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
  xsrfCookieName: CSRF_COOKIE_NAME,
  xsrfHeaderName: CSRF_HEADER_NAME,
})

function canRefreshRequest(config) {
  if (!config || config._authRetry || config._skipAuthRefresh) return false
  const path = String(config.url || '').split('?')[0]
  if (isRefreshEndpoint(config)) return false
  return !['/auth/login/', '/auth/signup/', '/auth/logout/'].some((endpoint) => path === endpoint || path.endsWith(endpoint))
}

const refreshCoordinator = createRefreshCoordinator(() => (
  apiClient.post('/auth/refresh/', null, { _authRetry: true })
))

export function refreshAccessCookie() {
  return refreshCoordinator.request()
}

export function resetRefreshState() {
  refreshCoordinator.reset()
}

apiClient.interceptors.request.use(async (config) => {
  const method = (config.method || 'get').toLowerCase()
  if (!unsafeMethods.has(method)) return config

  const token = await ensureCsrfCookie()
  if (token) {
    if (config.headers?.set) {
      config.headers.set(CSRF_HEADER_NAME, token)
    } else {
      config.headers = { ...config.headers, [CSRF_HEADER_NAME]: token }
    }
  }

  if (typeof FormData !== 'undefined' && config.data instanceof FormData && config.headers?.delete) {
    // Let the browser add the multipart boundary for file uploads.
    config.headers.delete('Content-Type')
  }

  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (isCsrfFailure(error) && error.config && !error.config._csrfRetry) {
      csrfToken = undefined
      try {
        await ensureCsrfCookie({ force: true })
        return apiClient({ ...error.config, _csrfRetry: true })
      } catch {
        // Return the original safe 403 when the browser cannot retain the CSRF cookie.
      }
    }

    if (error.response?.status === 401 && error.config?._authRetry && !isRefreshEndpoint(error.config)) {
      notifyAuthFailure()
    }

    if (error.response?.status === 401 && canRefreshRequest(error.config)) {
      try {
        await refreshAccessCookie()
        return apiClient({ ...error.config, _authRetry: true })
      } catch (refreshError) {
        if (refreshError?.status === 401) notifyAuthFailure()
        // Return the original 401 so the caller can show the correct auth state.
      }
    }

    return Promise.reject(normalizeApiError(error))
  },
)

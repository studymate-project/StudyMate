import axios from 'axios'
import {
  API_BASE_URL,
  API_TIMEOUT_MS,
  CSRF_BOOTSTRAP_PATH,
  CSRF_COOKIE_NAME,
  CSRF_HEADER_NAME,
} from './config'
import { normalizeApiError } from './errors'

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
let refreshRequest
let csrfToken

async function ensureCsrfCookie() {
  if (csrfToken) return csrfToken

  const existingToken = readCookie(CSRF_COOKIE_NAME)
  if (existingToken) return existingToken

  if (!csrfBootstrapRequest) {
    csrfBootstrapRequest = csrfBootstrapClient
      .get(CSRF_BOOTSTRAP_PATH)
      .then((response) => {
        csrfToken = response.data?.csrf_token || readCookie(CSRF_COOKIE_NAME)
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
  if (!config || config._authRetry) return false
  const path = config.url || ''
  return !['/auth/login/', '/auth/signup/', '/auth/refresh/', '/auth/logout/'].some((endpoint) => path.includes(endpoint))
}

async function refreshAccessCookie() {
  if (!refreshRequest) {
    refreshRequest = apiClient
      .post('/auth/refresh/', null, { _authRetry: true })
      .finally(() => {
        refreshRequest = undefined
      })
  }
  return refreshRequest
}

apiClient.interceptors.request.use(async (config) => {
  const method = (config.method || 'get').toLowerCase()
  if (!unsafeMethods.has(method)) return config

  const csrfToken = await ensureCsrfCookie()
  if (csrfToken) {
    if (config.headers?.set) {
      config.headers.set(CSRF_HEADER_NAME, csrfToken)
    } else {
      config.headers = { ...config.headers, [CSRF_HEADER_NAME]: csrfToken }
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
    if (error.response?.status === 401 && canRefreshRequest(error.config)) {
      try {
        await refreshAccessCookie()
        return apiClient({ ...error.config, _authRetry: true })
      } catch {
        // Return the original 401 so the caller can show the correct auth state.
      }
    }

    return Promise.reject(normalizeApiError(error))
  },
)

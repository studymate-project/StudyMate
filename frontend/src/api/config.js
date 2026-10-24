const configuredApiBaseUrl = import.meta.env?.VITE_API_BASE_URL

// The relative fallback supports same-origin deployments while local and
// cross-origin development should set VITE_API_BASE_URL explicitly.
export const API_BASE_URL = configuredApiBaseUrl || '/api'

export const API_TIMEOUT_MS = 10000
export const CSRF_COOKIE_NAME = 'csrftoken'
export const CSRF_HEADER_NAME = 'X-CSRFToken'
export const CSRF_BOOTSTRAP_PATH = '/auth/csrf/'

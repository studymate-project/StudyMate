import axios from 'axios'

function flattenError(value) {
  if (Array.isArray(value)) return value.map(flattenError).filter(Boolean).join(' ')
  if (value && typeof value === 'object') return Object.values(value).map(flattenError).filter(Boolean).join(' ')
  return typeof value === 'string' ? value : ''
}

function isUnsafeText(value) {
  return /<\/?(html|body|head|pre|title)\b|traceback|programmingerror|integrityerror|operationalerror|syntaxerror|select\s+.+\s+from|[a-z]:\\.+/i.test(value)
}

function statusMessage(status, fallbackMessage) {
  if (status >= 500) return 'Something went wrong. Please try again.'
  if (status === 401) return 'Authentication failed. Please try again.'
  if (status === 403) return 'You are not allowed to perform this action.'
  if (status === 404) return 'The requested service was not found.'
  if (status === 429) return 'Too many requests. Please wait a moment and try again.'
  return fallbackMessage
}

function getErrorMessage(data, status, fallbackMessage) {
  const safeStatusMessage = statusMessage(status, fallbackMessage)
  if (status >= 500 || status === 401 || status === 403 || status === 404 || status === 429) return safeStatusMessage
  if (typeof data === 'string' && data && !isUnsafeText(data)) return data
  if (!data || typeof data !== 'object') return fallbackMessage

  const detail = flattenError(data.detail)
  if (detail && !isUnsafeText(detail)) return detail
  if (typeof data.message === 'string' && !isUnsafeText(data.message)) return data.message
  const nonFieldErrors = flattenError(data.non_field_errors)
  if (nonFieldErrors && !isUnsafeText(nonFieldErrors)) return nonFieldErrors

  const firstFieldError = Object.values(data).map(flattenError).find((value) => value && !isUnsafeText(value))
  if (firstFieldError) return firstFieldError

  return safeStatusMessage
}

export class ApiError extends Error {
  constructor({ message, status, data, code, response, request, config }) {
    super(message)
    this.name = 'ApiError'
    this.isApiError = true
    this.status = status
    this.data = data
    this.code = code
    this.response = response
    this.request = request
    this.config = config
  }
}

export function normalizeApiError(error) {
  if (!axios.isAxiosError(error)) return error

  const data = error.response?.data
  const normalizedError = new ApiError({
    message: getErrorMessage(data, error.response?.status, 'The request could not be completed.'),
    status: error.response?.status,
    data,
    code: error.code,
    response: error.response,
    request: error.request,
    config: error.config,
  })
  if (import.meta.env.DEV) console.error('[StudyMate API]', error)
  return normalizedError
}

export function getApiErrorMessage(error) {
  if (error instanceof ApiError) return error.message
  const message = typeof error?.message === 'string' ? error.message : ''
  return message && !isUnsafeText(message) ? message : 'The request could not be completed.'
}

export function getApiFieldErrors(error) {
  const data = error?.data
  if (!data || typeof data !== 'object' || Array.isArray(data)) return {}

  return Object.fromEntries(
    Object.entries(data)
      .map(([field, value]) => [field, flattenError(value)])
      .filter(([, value]) => value && !isUnsafeText(value))
  )
}

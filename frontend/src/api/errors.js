import axios from 'axios'

function flattenError(value) {
  if (Array.isArray(value)) return value.map(flattenError).filter(Boolean).join(' ')
  if (value && typeof value === 'object') return Object.values(value).map(flattenError).filter(Boolean).join(' ')
  return typeof value === 'string' ? value : ''
}

function getErrorMessage(data, fallbackMessage) {
  if (typeof data === 'string' && data) return data
  if (!data || typeof data !== 'object') return fallbackMessage

  const detail = flattenError(data.detail)
  if (detail) return detail
  if (typeof data.message === 'string') return data.message
  const nonFieldErrors = flattenError(data.non_field_errors)
  if (nonFieldErrors) return nonFieldErrors

  const firstFieldError = Object.values(data).map(flattenError).find(Boolean)
  if (firstFieldError) return firstFieldError

  return fallbackMessage
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
  return new ApiError({
    message: getErrorMessage(data, error.message || 'The request could not be completed.'),
    status: error.response?.status,
    data,
    code: error.code,
    response: error.response,
    request: error.request,
    config: error.config,
  })
}

export function getApiErrorMessage(error) {
  return error instanceof ApiError ? error.message : error?.message || 'The request could not be completed.'
}

export function getApiFieldErrors(error) {
  const data = error?.data
  if (!data || typeof data !== 'object' || Array.isArray(data)) return {}

  return Object.fromEntries(
    Object.entries(data)
      .map(([field, value]) => [field, flattenError(value)])
      .filter(([, value]) => value)
  )
}

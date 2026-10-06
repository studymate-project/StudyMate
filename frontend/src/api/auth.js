import { apiClient } from './client'

let sessionRestoreRequest

function getUser(data) {
  return data?.user || null
}

export async function login(credentials) {
  const response = await apiClient.post('/auth/login/', credentials)
  return { ...response.data, user: getUser(response.data) }
}

export async function signup(payload) {
  const response = await apiClient.post('/auth/signup/', payload)
  return response.data
}

export async function getCurrentUser(config) {
  const response = await apiClient.get('/auth/me/', config)
  return getUser(response.data)
}

export async function refreshSession() {
  const response = await apiClient.post('/auth/refresh/')
  return response.data
}

async function restoreSessionOnce() {
  const restoreConfig = { _skipAuthRefresh: true }

  try {
    return await getCurrentUser(restoreConfig)
  } catch (error) {
    if (error?.status !== 401) throw error

    try {
      await refreshSession()
    } catch (refreshError) {
      // A visitor without an access or refresh cookie is expected to fail
      // refresh. Preserve other failures (including CSRF/configuration 403s)
      // so they are not mistaken for an anonymous session.
      if (refreshError?.status === 401) return null
      throw refreshError
    }

    return getCurrentUser(restoreConfig)
  }
}

export function restoreSession() {
  if (!sessionRestoreRequest) {
    sessionRestoreRequest = restoreSessionOnce().finally(() => {
      sessionRestoreRequest = undefined
    })
  }

  return sessionRestoreRequest
}

export async function logout() {
  const response = await apiClient.post('/auth/logout/')
  return response.data
}

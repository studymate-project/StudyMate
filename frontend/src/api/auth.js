import { apiClient } from './client'
import { clearNotificationCache } from './notifications'
import { clearQuestionListCache } from './questions'
import { clearResourceListCache } from './resources'

let sessionRestoreRequest
let currentUserRequest

function getUser(data) {
  return data?.user || null
}

export async function login(credentials) {
  clearResourceListCache()
  clearQuestionListCache()
  clearNotificationCache()
  const response = await apiClient.post('/auth/login/', credentials)
  return { ...response.data, user: getUser(response.data) }
}

export async function signup(payload) {
  const response = await apiClient.post('/auth/signup/', payload)
  return { ...response.data, status: response.status }
}

export async function requestSignupVerification(payload) {
  const response = await apiClient.post('/auth/signup/verification/request/', payload)
  return { ...response.data, status: response.status }
}

export async function verifySignupEmail(payload) {
  const response = await apiClient.post('/auth/signup/verification/verify/', payload)
  return { ...response.data, status: response.status }
}

export async function getCurrentUser(config) {
  if (currentUserRequest) return currentUserRequest

  const requestConfig = { ...config }
  currentUserRequest = apiClient.get('/auth/me/', requestConfig).then((response) => {
    return getUser(response.data)
  }).finally(() => {
    currentUserRequest = undefined
  })

  return currentUserRequest
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
  clearResourceListCache()
  clearQuestionListCache()
  clearNotificationCache()
  return response.data
}

import { QueryClient } from '@tanstack/react-query'

export const QUERY_STALE_TIMES = {
  lists: 60 * 1000,
  details: 2 * 60 * 1000,
  subjects: 10 * 60 * 1000,
  profile: 60 * 1000,
}

const MAX_QUERY_RETRIES = 2
const TRANSIENT_NETWORK_CODES = new Set([
  'ECONNABORTED',
  'ECONNRESET',
  'ENETUNREACH',
  'ETIMEDOUT',
  'EAI_AGAIN',
  'ERR_NETWORK',
])

function getHttpStatus(error) {
  return error?.status ?? error?.response?.status
}

function isCanceledRequest(error) {
  return error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError'
}

function isTransientNetworkError(error) {
  if (isCanceledRequest(error)) return false
  if (TRANSIENT_NETWORK_CODES.has(error?.code)) return true
  return Boolean(error?.request && !error?.response)
}

export function shouldRetryQuery(failureCount, error) {
  if (failureCount >= MAX_QUERY_RETRIES) return false

  const status = getHttpStatus(error)
  if (status === 401 || status === 403 || status === 429) return false
  if (status >= 500 && status <= 599) return true
  return !status && isTransientNetworkError(error)
}

export function getQueryRetryDelay(retryAttempt) {
  return Math.min(1000 * (2 ** retryAttempt), 5000)
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: QUERY_STALE_TIMES.lists,
      gcTime: typeof window === 'undefined' ? Infinity : 10 * 60 * 1000,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      retry: shouldRetryQuery,
      retryDelay: getQueryRetryDelay,
    },
    mutations: {
      retry: 0,
    },
  },
})

export function clearQueryCache() {
  queryClient.clear()
}

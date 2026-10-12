import { apiClient } from './client'

export const SEARCH_MAX_QUERY_LENGTH = 200
export const SEARCH_PAGE_SIZE = 20

export function normalizeSearchQuery(value) {
  return String(value ?? '').trim().replace(/\s+/g, ' ')
}

function normalizeSearchResult(result) {
  return {
    type: result?.type,
    id: result?.id,
    title: result?.title || '',
    snippet: result?.snippet || '',
    metadata: result?.metadata && typeof result.metadata === 'object' && !Array.isArray(result.metadata)
      ? result.metadata
      : {},
    detail_url: result?.detail_url || '',
    score: typeof result?.score === 'number' ? result.score : null,
  }
}

export function searchContent(query, { limit = SEARCH_PAGE_SIZE, offset = 0, signal } = {}) {
  const normalizedQuery = normalizeSearchQuery(query)

  if (!normalizedQuery) return Promise.reject(new Error('A search query is required.'))
  if (normalizedQuery.length > SEARCH_MAX_QUERY_LENGTH) {
    return Promise.reject(new Error(`Search queries must be ${SEARCH_MAX_QUERY_LENGTH} characters or fewer.`))
  }

  return apiClient
    .get('/search/', {
      params: { q: normalizedQuery, limit, offset },
      signal,
    })
    .then((response) => {
      const data = response.data || {}
      const results = Array.isArray(data.results) ? data.results.map(normalizeSearchResult) : []

      return {
        query: typeof data.query === 'string' ? data.query : normalizedQuery,
        results,
        limit: Number.isInteger(data.limit) ? data.limit : limit,
        offset: Number.isInteger(data.offset) ? data.offset : offset,
        hasMore: Boolean(data.has_more),
        nextOffset: Number.isInteger(data.next_offset) ? data.next_offset : null,
      }
    })
}

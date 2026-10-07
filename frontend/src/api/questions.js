import { apiClient } from './client'

const inFlightRequests = new Map()
const questionListCache = new Map()
const QUESTION_LIST_CACHE_TTL_MS = 30 * 1000
let questionCacheGeneration = 0

function formatDate(value) {
  if (!value) return null

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null

  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

function normalizeAuthor(author) {
  if (!author) return null

  const name = [author.first_name, author.last_name].filter(Boolean).join(' ')
  return {
    id: author.id,
    username: author.username,
    name: name || author.username || 'StudyMate member',
  }
}

export function normalizeAnswer(answer) {
  return {
    id: answer.id,
    questionId: answer.question,
    author: normalizeAuthor(answer.author),
    body: answer.body,
    isHelpful: answer.is_helpful,
    upvotes: answer.upvotes ?? null,
    createdAt: formatDate(answer.created_at),
    questionTitle: answer.question_title || '',
    questionSlug: answer.question_slug || '',
  }
}

export function normalizeQuestion(question) {
  const answerList = Array.isArray(question.answers) ? question.answers.map(normalizeAnswer) : []

  return {
    id: question.id,
    title: question.title,
    slug: question.slug,
    body: question.body,
    subject: question.subject,
    topic: question.topic,
    academicLevel: question.academic_level ?? null,
    tags: Array.isArray(question.tags) ? question.tags.map((tag) => tag.name).filter(Boolean) : [],
    author: normalizeAuthor(question.author),
    createdAt: formatDate(question.created_at),
    upvotes: question.upvotes ?? null,
    answerCount: Array.isArray(question.answers) ? answerList.length : question.answers ?? 0,
    answers: answerList,
  }
}

function normalizeQuestionResponse(data) {
  const results = Array.isArray(data) ? data : data?.results || []

  return {
    questions: results.map(normalizeQuestion),
    pagination: {
      count: Array.isArray(data) ? results.length : data?.count || 0,
      next: Array.isArray(data) ? null : data?.next || null,
      previous: Array.isArray(data) ? null : data?.previous || null,
    },
  }
}

export function listQuestions(params = {}) {
  const query = Object.fromEntries(Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ''))
  const requestKey = JSON.stringify(query)
  const cached = questionListCache.get(requestKey)
  if (cached && cached.expiresAt > Date.now()) return Promise.resolve(cached.data)
  const existingRequest = inFlightRequests.get(`list:${requestKey}`)
  if (existingRequest) return existingRequest

  const requestGeneration = questionCacheGeneration
  const request = apiClient
    .get('/questions/', { params: query })
    .then((response) => {
      const data = normalizeQuestionResponse(response.data)
      if (requestGeneration === questionCacheGeneration) {
        questionListCache.set(requestKey, { data, expiresAt: Date.now() + QUESTION_LIST_CACHE_TTL_MS })
      }
      return data
    })
  inFlightRequests.set(`list:${requestKey}`, request)
  request.then(
    () => inFlightRequests.delete(`list:${requestKey}`),
    () => inFlightRequests.delete(`list:${requestKey}`),
  )
  return request
}

export function clearQuestionListCache() {
  questionListCache.clear()
  questionCacheGeneration += 1
  inFlightRequests.forEach((request, key) => {
    if (String(key).startsWith('list:')) inFlightRequests.delete(key)
  })
}

export function createQuestion(payload) {
  return apiClient
    .post('/questions/', payload)
    .then((response) => {
      clearQuestionListCache()
      return normalizeQuestion(response.data)
    })
}

export function getQuestionBySlug(slug) {
  const normalizedSlug = slug?.trim()
  if (!normalizedSlug) return Promise.reject(new Error('A question slug is required.'))

  const requestKey = `question-detail:${normalizedSlug}`
  const existingRequest = inFlightRequests.get(requestKey)
  if (existingRequest) return existingRequest

  const request = apiClient
    .get(`/questions/${encodeURIComponent(normalizedSlug)}/`)
    .then((response) => normalizeQuestion(response.data))

  inFlightRequests.set(requestKey, request)
  request.then(
    () => inFlightRequests.delete(requestKey),
    () => inFlightRequests.delete(requestKey),
  )

  return request
}

export async function listAnswers(questionId) {
  if (questionId === null || questionId === undefined) return Promise.reject(new Error('A question ID is required.'))

  const answers = []
  let page = 1
  let count = 0
  let hasNextPage = true

  while (hasNextPage) {
    const response = await apiClient.get(`/questions/${encodeURIComponent(questionId)}/answers/`, {
      params: { page, page_size: 100 },
    })
    const data = response.data
    const results = Array.isArray(data) ? data : Array.isArray(data?.results) ? data.results : []
    answers.push(...results.map(normalizeAnswer))
    count = Array.isArray(data) ? answers.length : data?.count ?? answers.length
    hasNextPage = !Array.isArray(data) && Boolean(data?.next)
    page += 1
  }

  return { answers, count }
}

export function listAnswersByAuthor() {
  return apiClient
    .get('/questions/answers/')
    .then((response) => {
      const data = response.data
      const results = Array.isArray(data) ? data : data?.results || []
      return {
        answers: results.map(normalizeAnswer),
        count: Array.isArray(data) ? results.length : data?.count ?? results.length,
      }
    })
}

export function createAnswer(questionId, body) {
  return apiClient
    .post(`/questions/${questionId}/answers/`, { body })
    .then((response) => {
      clearQuestionListCache()
      return normalizeAnswer(response.data)
    })
}

export function upvoteQuestion(questionId) {
  return apiClient.post(`/questions/${questionId}/upvote/`).then((response) => {
    clearQuestionListCache()
    return response.data
  })
}

export function removeQuestionUpvote(questionId) {
  return apiClient.delete(`/questions/${questionId}/upvote/`).then((response) => {
    clearQuestionListCache()
    return response.data
  })
}

export function upvoteAnswer(questionId, answerId) {
  return apiClient.post(`/questions/${questionId}/answers/${answerId}/upvote/`).then((response) => response.data)
}

export function removeAnswerUpvote(questionId, answerId) {
  return apiClient.delete(`/questions/${questionId}/answers/${answerId}/upvote/`).then((response) => response.data)
}

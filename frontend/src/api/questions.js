import { apiClient } from './client'
import { queryClient, QUERY_STALE_TIMES } from '../query/queryClient'
import { questionKeys } from '../query/queryKeys'

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

function normalizeParams(params) {
  return Object.fromEntries(Object.entries(params || {}).filter(([, value]) => value !== undefined && value !== null && value !== ''))
}

export function fetchQuestionList(params = {}) {
  const query = normalizeParams(params)
  return apiClient
    .get('/questions/', { params: query })
    .then((response) => normalizeQuestionResponse(response.data))
}

export function listQuestions(params = {}) {
  const query = normalizeParams(params)
  return queryClient.fetchQuery({
    queryKey: questionKeys.list(query),
    queryFn: () => fetchQuestionList(query),
    staleTime: QUERY_STALE_TIMES.lists,
  })
}

export function clearQuestionListCache() {
  queryClient.invalidateQueries({ queryKey: questionKeys.lists(), refetchType: 'active' })
  queryClient.invalidateQueries({ queryKey: questionKeys.answers(), refetchType: 'active' })
  queryClient.invalidateQueries({ queryKey: [...questionKeys.all, 'author-answers'], refetchType: 'active' })
  queryClient.invalidateQueries({ queryKey: questionKeys.details(), refetchType: 'active' })
}

export function createQuestion(payload) {
  return apiClient
    .post('/questions/', payload)
    .then((response) => {
      clearQuestionListCache()
      return normalizeQuestion(response.data)
    })
}

export function fetchQuestionDetail(slug) {
  return apiClient
    .get(`/questions/${encodeURIComponent(slug)}/`)
    .then((response) => normalizeQuestion(response.data))
}

export function getQuestionBySlug(slug) {
  const normalizedSlug = slug?.trim()
  if (!normalizedSlug) return Promise.reject(new Error('A question slug is required.'))

  return queryClient.fetchQuery({
    queryKey: questionKeys.detail(normalizedSlug),
    queryFn: () => fetchQuestionDetail(normalizedSlug),
    staleTime: QUERY_STALE_TIMES.details,
  })
}

export async function fetchQuestionAnswers(questionId) {
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

export function listAnswers(questionId) {
  if (questionId === null || questionId === undefined) return Promise.reject(new Error('A question ID is required.'))

  return queryClient.fetchQuery({
    queryKey: questionKeys.answerList(questionId),
    queryFn: () => fetchQuestionAnswers(questionId),
    staleTime: QUERY_STALE_TIMES.details,
  })
}

export function fetchAnswersByAuthor(params = {}) {
  const query = normalizeParams(params)
  return apiClient
    .get('/questions/answers/', { params: query })
    .then((response) => {
      const data = response.data
      const results = Array.isArray(data) ? data : data?.results || []
      return {
        answers: results.map(normalizeAnswer),
        count: Array.isArray(data) ? results.length : data?.count ?? results.length,
        pagination: {
          count: Array.isArray(data) ? results.length : data?.count || 0,
          next: Array.isArray(data) ? null : data?.next || null,
          previous: Array.isArray(data) ? null : data?.previous || null,
        },
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

export function listAnswersByAuthor(userId = 'current', params = {}) {
  const query = normalizeParams(params)
  return queryClient.fetchQuery({
    queryKey: questionKeys.authorAnswers(userId, query),
    queryFn: () => fetchAnswersByAuthor(query),
    staleTime: QUERY_STALE_TIMES.profile,
  })
}

export function removeQuestionUpvote(questionId) {
  return apiClient.delete(`/questions/${questionId}/upvote/`).then((response) => {
    clearQuestionListCache()
    return response.data
  })
}

export function upvoteAnswer(questionId, answerId) {
  return apiClient.post(`/questions/${questionId}/answers/${answerId}/upvote/`).then((response) => {
    queryClient.invalidateQueries({ queryKey: questionKeys.answerList(questionId), refetchType: 'active' })
    queryClient.invalidateQueries({ queryKey: questionKeys.details(), refetchType: 'active' })
    return response.data
  })
}

export function removeAnswerUpvote(questionId, answerId) {
  return apiClient.delete(`/questions/${questionId}/answers/${answerId}/upvote/`).then((response) => {
    queryClient.invalidateQueries({ queryKey: questionKeys.answerList(questionId), refetchType: 'active' })
    queryClient.invalidateQueries({ queryKey: questionKeys.details(), refetchType: 'active' })
    return response.data
  })
}

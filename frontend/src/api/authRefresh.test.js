import assert from 'node:assert/strict'
import test from 'node:test'
import { createRefreshCoordinator, getRetryAfterMs, isRefreshEndpoint } from './authRefresh.js'
import { restoreSessionWithRefresh } from './authFlow.js'

test('concurrent refresh callers share one in-flight request', async () => {
  let calls = 0
  let resolveRefresh
  const coordinator = createRefreshCoordinator(() => {
    calls += 1
    return new Promise((resolve) => { resolveRefresh = resolve })
  })

  const first = coordinator.request()
  const second = coordinator.request()
  assert.strictEqual(first, second)
  await Promise.resolve()
  resolveRefresh({ ok: true })

  await Promise.all([first, second])
  assert.equal(calls, 1)
})

test('refresh 401 is remembered until a successful login resets the coordinator', async () => {
  let calls = 0
  const error = { status: 401 }
  const coordinator = createRefreshCoordinator(async () => {
    calls += 1
    throw error
  })

  await assert.rejects(coordinator.request(), (received) => received === error)
  await assert.rejects(coordinator.request(), (received) => received === error)
  assert.equal(calls, 1)

  coordinator.reset()
  await assert.rejects(coordinator.request(), (received) => received === error)
  assert.equal(calls, 2)
})

test('refresh 403 is remembered so a CSRF failure cannot trigger repeated requests', async () => {
  let calls = 0
  const error = { status: 403 }
  const coordinator = createRefreshCoordinator(async () => {
    calls += 1
    throw error
  })

  await assert.rejects(coordinator.request(), (received) => received === error)
  await assert.rejects(coordinator.request(), (received) => received === error)
  assert.equal(calls, 1)

  coordinator.reset()
  await assert.rejects(coordinator.request(), (received) => received === error)
  assert.equal(calls, 2)
})

test('refresh 429 honors Retry-After and does not immediately retry', async () => {
  let now = 1_000
  let calls = 0
  const error = { status: 429, response: { headers: { 'retry-after': '5' } } }
  const coordinator = createRefreshCoordinator(async () => {
    calls += 1
    throw error
  }, { now: () => now })

  assert.equal(getRetryAfterMs(error, now), 5_000)
  await assert.rejects(coordinator.request(), (received) => received === error)
  await assert.rejects(coordinator.request(), (received) => received === error)
  assert.equal(calls, 1)

  now += 5_000
  await assert.rejects(coordinator.request(), (received) => received === error)
  assert.equal(calls, 2)
})

test('session restore treats missing or throttled refresh as unauthenticated', async () => {
  let refreshCalls = 0
  const getCurrentUser = async () => { throw { status: 401 } }

  const missing = await restoreSessionWithRefresh({
    getCurrentUser,
    refreshSession: async () => {
      refreshCalls += 1
      throw { status: 401 }
    },
  })
  const throttled = await restoreSessionWithRefresh({
    getCurrentUser,
    refreshSession: async () => {
      refreshCalls += 1
      throw { status: 429 }
    },
  })

  assert.equal(missing, null)
  assert.equal(throttled, null)
  assert.equal(refreshCalls, 2)
})

test('session restore retries /me at most once and does not refresh the refresh endpoint', async () => {
  let userCalls = 0
  let refreshCalls = 0
  const user = { id: 1 }
  const restored = await restoreSessionWithRefresh({
    getCurrentUser: async () => {
      userCalls += 1
      if (userCalls === 1) throw { status: 401 }
      return user
    },
    refreshSession: async () => { refreshCalls += 1 },
  })

  assert.deepEqual(restored, user)
  assert.equal(userCalls, 2)
  assert.equal(refreshCalls, 1)
  assert.equal(isRefreshEndpoint({ url: '/auth/refresh/' }), true)
  assert.equal(isRefreshEndpoint({ url: 'https://api.example.test/api/auth/refresh/' }), true)
  assert.equal(isRefreshEndpoint({ url: '/api/resources/' }), false)
})

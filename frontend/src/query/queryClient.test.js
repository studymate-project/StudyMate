import assert from 'node:assert/strict'
import test from 'node:test'
import { getQueryRetryDelay, shouldRetryQuery } from './queryClient.js'

test('query retries do not repeat authentication or throttling failures', () => {
  for (const error of [
    { status: 401 },
    { status: 403 },
    { status: 429 },
    { response: { status: 401 } },
    { response: { status: 403 } },
    { response: { status: 429 } },
  ]) {
    assert.equal(shouldRetryQuery(0, error), false)
  }
})

test('query retries are bounded to transient network and server failures', () => {
  const networkError = { code: 'ERR_NETWORK' }

  assert.equal(shouldRetryQuery(0, networkError), true)
  assert.equal(shouldRetryQuery(1, networkError), true)
  assert.equal(shouldRetryQuery(2, networkError), false)
  assert.equal(shouldRetryQuery(0, { status: 503 }), true)
  assert.equal(shouldRetryQuery(0, { status: 400 }), false)
  assert.equal(shouldRetryQuery(0, new Error('unexpected failure')), false)
})

test('query retry delay uses bounded exponential backoff', () => {
  assert.deepEqual(
    [0, 1, 2, 3, 4].map(getQueryRetryDelay),
    [1000, 2000, 4000, 5000, 5000],
  )
})

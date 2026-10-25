import assert from 'node:assert/strict'
import test from 'node:test'
import { getLoginState, getLocationPath, getPostAuthDestination } from './navigation.js'

test('public home and protected action locations preserve the full internal path', () => {
  const location = { pathname: '/', search: '?subject=java', hash: '#popular' }
  assert.equal(getLocationPath(location), '/?subject=java#popular')
  assert.deepEqual(getLoginState(location), { from: '/?subject=java#popular' })
})

test('completed users return to a safe protected destination after login', () => {
  const user = { profile: { onboarding_completed: true } }
  assert.equal(getPostAuthDestination(user, '/saved?tab=notes'), '/saved?tab=notes')
  assert.equal(getPostAuthDestination(user, 'https://example.test/account'), '/home')
  assert.equal(getPostAuthDestination(user, '/\\evil.example/account'), '/home')
  assert.equal(getPostAuthDestination(user, '/login'), '/home')
})

test('new users always complete onboarding before reaching home', () => {
  assert.equal(getPostAuthDestination({ profile: { onboarding_completed: false } }, '/saved'), '/onboarding')
  assert.equal(getPostAuthDestination(null, '/saved'), '/onboarding')
})

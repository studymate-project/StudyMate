import assert from 'node:assert/strict'
import test from 'node:test'

import { confirmProfileResourceDeletion, profileResourceOpenTarget } from './profileResourceActions.js'

test('profile resource deletion requires confirmation', () => {
  const resource = { title: 'Private notes' }
  assert.equal(confirmProfileResourceDeletion(resource, () => false), false)
  assert.equal(confirmProfileResourceDeletion(resource, () => true), true)
})

test('profile resource action opens links, videos, and resources correctly', () => {
  assert.equal(profileResourceOpenTarget({ resourceType: 'link', resourceUrl: 'https://example.test' }), 'https://example.test')
  assert.equal(profileResourceOpenTarget({ targetType: 'video', slug: 'lesson' }), '/videos/lesson')
  assert.equal(profileResourceOpenTarget({ targetType: 'resource', slug: 'notes' }), '/resources/notes')
})

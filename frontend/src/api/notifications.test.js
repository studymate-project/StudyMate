import assert from 'node:assert/strict'
import test from 'node:test'

import { getNotificationCategory, getNotificationTarget, matchesNotificationTab, openNotificationTarget } from './notificationTargets.js'

function notification(overrides = {}) {
  return {
    id: 1,
    notification_type: 'resource_saved',
    actor: { id: 2, username: 'actor' },
    message: 'A resource was saved.',
    created_at: '2026-01-01T00:00:00Z',
    is_read: false,
    payload: {},
    ...overrides,
  }
}

test('classifies file, video, and external resource targets for the Resources filter', () => {
  const file = getNotificationTarget(notification({
    target: { kind: 'resource', resource_type: 'file', url: '/resources/file-notes' },
  }), null)
  const video = getNotificationTarget(notification({
    target: { kind: 'video', resource_type: 'video', url: '/videos/lesson-video' },
  }), null)
  const external = getNotificationTarget(notification({
    target: { kind: 'external', resource_type: 'link', url: 'https://example.edu/notes' },
  }), null)

  assert.deepEqual(file, { kind: 'resource', url: '/resources/file-notes', resourceType: 'file' })
  assert.deepEqual(video, { kind: 'video', url: '/videos/lesson-video', resourceType: 'video' })
  assert.deepEqual(external, { kind: 'external', url: 'https://example.edu/notes', resourceType: 'link' })
  assert.equal(getNotificationCategory('unknown_type', file), 'Resources')
  assert.equal(getNotificationCategory('unknown_type', video), 'Resources')
  assert.equal(getNotificationCategory('unknown_type', external), 'Resources')
  assert.equal(matchesNotificationTab({ type: 'Upvotes', targetKind: 'resource' }, 'Resources'), true)
  assert.equal(matchesNotificationTab({ type: 'Upvotes', targetKind: 'video' }, 'Resources'), true)
  assert.equal(matchesNotificationTab({ type: 'Upvotes', targetKind: 'external' }, 'Resources'), true)
})

test('rejects malformed or unsafe notification targets', () => {
  assert.equal(getNotificationTarget(notification({
    target: { kind: 'resource', url: '//untrusted.example/path' },
  }), null), null)
  assert.equal(getNotificationTarget(notification({
    target: { kind: 'external', url: 'javascript:alert(1)' },
  }), null), null)
  assert.equal(getNotificationTarget(notification({
    target: { kind: 'external', url: 'https://user:password@example.edu/path' },
  }), null), null)
})

test('opens external targets in a protected new window and navigates internal targets', () => {
  const opened = []
  globalThis.window = { open: (...args) => opened.push(args) }
  const navigated = []

  assert.equal(openNotificationTarget({ target: 'https://example.edu/path', targetKind: 'external' }, (url) => navigated.push(url)), true)
  assert.deepEqual(opened, [['https://example.edu/path', '_blank', 'noopener,noreferrer']])

  assert.equal(openNotificationTarget({ target: '/videos/lesson-video', targetKind: 'video' }, (url) => navigated.push(url)), true)
  assert.deepEqual(navigated, ['/videos/lesson-video'])

  delete globalThis.window
})

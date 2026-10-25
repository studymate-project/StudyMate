import assert from 'node:assert/strict'
import test from 'node:test'

import { apiClient } from './client.js'
import { clearResourceListCache, deleteResource, listAllSavedResources, listSavedResources, normalizeResource } from './resources.js'

test('resource normalization preserves mixed resource types and open metadata', () => {
  const file = normalizeResource({ id: 1, slug: 'notes', title: 'Notes', resource_type: 'pdf', file: '/media/notes.pdf', uploader: { id: 4, username: 'owner' } })
  const link = normalizeResource({ id: 2, slug: 'reference', title: 'Reference', resource_type: 'link', external_url: 'https://example.test/reference', uploader: { id: 4, username: 'owner' } })
  const video = normalizeResource({ id: 3, slug: 'lesson', title: 'Lesson', resource_type: 'video', uploader: { id: 4, username: 'owner' } })

  assert.deepEqual([file.targetType, link.resourceType, link.resourceUrl, video.type], ['resource', 'link', 'https://example.test/reference', 'Video'])
})

test('saved resource pagination is collected without duplicate concurrent requests', async () => {
  clearResourceListCache()
  const originalGet = apiClient.get
  const calls = []
  apiClient.get = async (url, config) => {
    calls.push({ url, params: config.params })
    const page = config.params.page
    return {
      data: page === 1
        ? { count: 2, next: '/api/saved-resources/?page=2', previous: null, results: [{ id: 1, slug: 'one', title: 'One', resource_type: 'notes', uploader: { id: 4, username: 'owner' } }] }
        : { count: 2, next: null, previous: '/api/saved-resources/?page=1', results: [{ id: 2, slug: 'two', title: 'Two', resource_type: 'link', external_url: 'https://example.test/two', uploader: { id: 4, username: 'owner' } }] },
    }
  }

  try {
    const first = listSavedResources({ page: 1, page_size: 100 })
    const second = listSavedResources({ page: 1, page_size: 100 })
    assert.strictEqual(first, second)
    const result = await listAllSavedResources()
    assert.deepEqual(result.resources.map((resource) => resource.id), [1, 2])
    assert.equal(calls.length, 2)
  } finally {
    apiClient.get = originalGet
    clearResourceListCache()
  }
})

test('resource deletion uses the backend resource endpoint', async () => {
  const originalDelete = apiClient.delete
  let endpoint
  apiClient.delete = async (url) => { endpoint = url; return { data: null } }
  try {
    await deleteResource(42)
    assert.equal(endpoint, '/resources/42/')
  } finally {
    apiClient.delete = originalDelete
  }
})

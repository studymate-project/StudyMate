import assert from 'node:assert/strict'
import test from 'node:test'

import { apiClient } from './client.js'
import { clearVideoListCache, listVideos } from './videos.js'

function videoResponse() {
  return {
    data: {
      count: 1,
      next: null,
      previous: null,
      results: [{
        id: 7,
        slug: 'local-video',
        title: 'Local video',
        youtube_video_id: 'dQw4w9WgXcQ',
        subject: 'Physics',
        tags: [],
      }],
    },
  }
}

test('concurrent video list requests are coalesced without cross-user caching', async () => {
  clearVideoListCache()
  const originalGet = apiClient.get
  let calls = 0
  let resolveRequest
  apiClient.get = () => {
    calls += 1
    if (calls > 1) return Promise.resolve(videoResponse())
    return new Promise((resolve) => { resolveRequest = resolve })
  }

  try {
    const first = listVideos({ page: 1, page_size: 20, unused: 'ignored' })
    const second = listVideos({ page_size: 20, page: 1 })
    assert.strictEqual(first, second)
    assert.equal(calls, 1)
    resolveRequest(videoResponse())
    await first

    await listVideos({ page: 1, page_size: 20 })
    assert.equal(calls, 2)
  } finally {
    apiClient.get = originalGet
    clearVideoListCache()
  }
})

test('clearing the video list cache invalidates in-flight results', async () => {
  clearVideoListCache()
  const originalGet = apiClient.get
  let calls = 0
  let resolveRequest
  apiClient.get = () => {
    calls += 1
    return new Promise((resolve) => { resolveRequest = resolve })
  }

  try {
    const request = listVideos({ page: 1 })
    clearVideoListCache()
    resolveRequest(videoResponse())
    await request

    apiClient.get = async () => {
      calls += 1
      return videoResponse()
    }
    await listVideos({ page: 1 })
    assert.equal(calls, 2)
  } finally {
    apiClient.get = originalGet
    clearVideoListCache()
  }
})

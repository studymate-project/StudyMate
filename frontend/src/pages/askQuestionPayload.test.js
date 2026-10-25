import assert from 'node:assert/strict'
import test from 'node:test'

import { buildAskQuestionPayload } from './askQuestionPayload.js'

test('Ask Question submission keeps supported fields without Task or Tag payloads', () => {
  const payload = buildAskQuestionPayload({ title: '  How? ', body: '  Need help. ', subject: 'Java', topic: 'OOP', tags: 'java' })

  assert.deepEqual(payload, { title: 'How?', body: 'Need help.', subject: 'Java' })
  assert.equal('topic' in payload, false)
  assert.equal('tags' in payload, false)
  assert.equal('tag_names' in payload, false)
})

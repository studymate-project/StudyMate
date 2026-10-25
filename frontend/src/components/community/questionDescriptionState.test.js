import assert from 'node:assert/strict'
import test from 'node:test'

import { getQuestionDescriptionToggleLabel, toggleQuestionDescription } from './questionDescriptionState.js'

test('long descriptions start collapsed and toggle between More and Less', () => {
  assert.equal(getQuestionDescriptionToggleLabel(true, false), 'More')
  assert.equal(toggleQuestionDescription(false), true)
  assert.equal(getQuestionDescriptionToggleLabel(true, true), 'Less')
  assert.equal(toggleQuestionDescription(true), false)
})

test('short descriptions have no toggle and remain collapsed', () => {
  assert.equal(getQuestionDescriptionToggleLabel(false, false), '')
  assert.equal(toggleQuestionDescription(false, false), false)
})

test('description state is independent for separate question cards', () => {
  let firstExpanded = false
  let secondExpanded = false
  firstExpanded = toggleQuestionDescription(firstExpanded)

  assert.equal(firstExpanded, true)
  assert.equal(secondExpanded, false)
})

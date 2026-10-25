export function getQuestionDescriptionToggleLabel(hasOverflow, expanded) {
  if (!hasOverflow) return ''
  return expanded ? 'Less' : 'More'
}

export function toggleQuestionDescription(expanded, hasOverflow = true) {
  return hasOverflow ? !expanded : false
}

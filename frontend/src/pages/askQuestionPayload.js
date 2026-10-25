export function buildAskQuestionPayload(form) {
  return {
    title: form.title.trim(),
    body: form.body.trim(),
    subject: form.subject,
  }
}

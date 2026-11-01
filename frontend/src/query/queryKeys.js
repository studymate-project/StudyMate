export const resourceKeys = {
  all: ['resources'],
  lists: () => [...resourceKeys.all, 'list'],
  list: (params) => [...resourceKeys.lists(), params],
  details: () => [...resourceKeys.all, 'detail'],
  detail: (slug) => [...resourceKeys.details(), slug],
  savedLists: () => [...resourceKeys.all, 'saved'],
  savedList: (params) => [...resourceKeys.savedLists(), params],
}

export const videoKeys = {
  all: ['videos'],
  lists: () => [...videoKeys.all, 'list'],
  list: (params) => [...videoKeys.lists(), params],
  details: () => [...videoKeys.all, 'detail'],
  detail: (slug) => [...videoKeys.details(), slug],
}

export const questionKeys = {
  all: ['questions'],
  lists: () => [...questionKeys.all, 'list'],
  list: (params) => [...questionKeys.lists(), params],
  details: () => [...questionKeys.all, 'detail'],
  detail: (slug) => [...questionKeys.details(), slug],
  answers: () => [...questionKeys.all, 'answers'],
  answerList: (questionId) => [...questionKeys.answers(), questionId],
  authorAnswers: (userId, params = {}) => [...questionKeys.all, 'author-answers', userId, params],
}

export const profileKeys = {
  all: ['profiles'],
  current: (userId) => [...profileKeys.all, 'current', userId],
  currentSection: (userId, section) => [...profileKeys.current(userId), section],
  public: (username) => [...profileKeys.all, 'public', username],
}

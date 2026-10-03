import { resources } from './resources'
import { users } from './users'
import { videos } from './videos'

export const formatNumber = (value) => Number(value).toLocaleString('en-IN')

export const getUserById = (id) => users.find((user) => user.id === id)
export const getUserByUsername = (username) => users.find((user) => user.username === username)
export const getResourceBySlug = (slug) => resources.find((resource) => resource.slug === slug)
export const getVideoBySlug = (slug) => videos.find((video) => video.slug === slug)
export const getResourcesByIds = (ids = []) => ids.map((id) => resources.find((resource) => resource.id === id)).filter(Boolean)
export const getVideosByIds = (ids = []) => ids.map((id) => videos.find((video) => video.id === id)).filter(Boolean)

export const getResourcesByUserId = (userId) => resources.filter((resource) => resource.authorId === userId)
export const withAuthor = (items) =>
  items.map((item) => ({
    ...item,
    author: getUserById(item.authorId),
  }))

export const searchAll = (query) => {
  const q = query.trim().toLowerCase()
  const matches = (fields) => fields.filter(Boolean).join(' ').toLowerCase().includes(q)

  if (!q) {
    return {
      resources,
      videos,
      questions: [],
      users,
    }
  }

  return {
    resources: resources.filter((resource) => matches([resource.title, resource.subject, resource.topic, resource.type, ...resource.tags])),
    videos: videos.filter((video) => matches([video.title, video.subject, video.topic, ...video.tags])),
    questions: [],
    users: users.filter((user) => matches([user.name, user.course, user.semester])),
  }
}

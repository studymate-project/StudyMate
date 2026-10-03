const youtubeHosts = new Set(['youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be', 'www.youtu.be'])
const videoIdPattern = /^[a-zA-Z0-9_-]{11}$/

export const isValidYouTubeVideoId = (value) => videoIdPattern.test(value || '')

export function parseYouTubeUrl(value) {
  if (!value?.trim()) return null

  try {
    const normalizedUrl = value.trim().match(/^https?:\/\//i) ? value.trim() : `https://${value.trim()}`
    const url = new URL(normalizedUrl)
    const host = url.hostname.toLowerCase()
    if (!youtubeHosts.has(host)) return null

    const videoId = host.includes('youtu.be')
      ? url.pathname.split('/').filter(Boolean)[0]
      : url.pathname.startsWith('/shorts/') || url.pathname.startsWith('/embed/')
        ? url.pathname.split('/').filter(Boolean)[1]
        : url.searchParams.get('v')

    if (!videoIdPattern.test(videoId || '')) return null
    return { url: url.toString(), videoId, provider: 'youtube' }
  } catch {
    return null
  }
}

export const getYouTubeEmbedUrl = (videoId) => (
  isValidYouTubeVideoId(videoId) ? `https://www.youtube-nocookie.com/embed/${videoId}` : null
)

import { getYouTubeEmbedUrl } from '../../utils/youtubeUtils'

function YouTubePlayer({ videoId, title }) {
  const embedUrl = getYouTubeEmbedUrl(videoId)

  if (!embedUrl) {
    return <div className="flex aspect-video w-full items-center justify-center border-2 border-[var(--color-border)] bg-black px-5 text-center text-sm font-black text-[var(--color-text)]">This video is not available for playback.</div>
  }

  return <div className="aspect-video w-full overflow-hidden border-2 border-[var(--color-border)] bg-black"><iframe className="h-full w-full" src={embedUrl} title={`${title} — YouTube video player`} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowFullScreen referrerPolicy="strict-origin-when-cross-origin" /></div>
}

export default YouTubePlayer

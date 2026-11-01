import { Link } from 'react-router-dom'
import YouTubePlayer from './YouTubePlayer'

function VideoCard({ video }) {
  return (
    <article className="flex w-full min-w-0 flex-col overflow-hidden rounded-xl bg-[var(--color-surface)]">
      <YouTubePlayer videoId={video.youtubeVideoId} title={video.title} />
      <div className="min-w-0 flex-1 p-3 sm:p-4">
        <h3 className="min-h-[3.5rem] text-base font-black leading-snug text-white">
          <Link
            to={`/videos/${video.slug}`}
            className="rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
          >
            {video.title}
          </Link>
        </h3>
        <p className="mt-1 truncate text-sm font-black text-[var(--color-text)]">
          {video.subject} <span aria-hidden="true">-</span> {video.topic}
        </p>
      </div>
    </article>
  )
}

export default VideoCard

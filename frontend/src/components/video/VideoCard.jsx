import { Link } from 'react-router-dom'
import Avatar from '../common/Avatar'
import YouTubePlayer from './YouTubePlayer'

function VideoCard({ video, className = '' }) {
  return (
    <article className={`flex h-full w-full min-w-0 flex-col overflow-hidden rounded-xl bg-[var(--color-surface)] ${className}`}>
      <YouTubePlayer videoId={video.youtubeVideoId} title={video.title} />
      <div className="min-w-0 flex-1 p-3 sm:p-4">
        <h3 className="h-[3.5rem] line-clamp-2 text-xl font-black leading-snug text-white">
          <Link
            to={`/videos/${video.slug}`}
            className="rounded focus-visible:outline focus-visible:outline-2 text-xl focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
          >
            {video.title}
          </Link>
        </h3>
        <p className="mt-1 truncate text-sm font-black text-[var(--color-text)]">
          {video.subject} <span aria-hidden="true">-</span> {video.topic}
        </p>
        {video.author ? <p className="mt-2 flex items-center gap-2 truncate text-sm font-black text-[var(--color-text)]"><Avatar user={video.author} size="xs" decorative />{video.author.name}</p> : null}
      </div>
    </article>
  )
}

export default VideoCard

import { Link } from 'react-router-dom'
import { getApiErrorMessage } from '../../api'
import Spinner from '../common/Spinner'
import YouTubePlayer from '../video/YouTubePlayer'

function VideoList({ videos, loading, error }) {
  return (
    <section className="mt-7" aria-labelledby="explore-videos-heading">
      <h2 id="explore-videos-heading" className="text-sm font-black text-white">Videos</h2>
      {loading ? <div className="flex justify-center py-8"><Spinner label="Loading videos" /></div> : null}
      {!loading && error ? <p className="mt-3 text-sm font-black text-[var(--color-text)]">{getApiErrorMessage(error)}</p> : null}
      {!loading && !error && videos.length === 0 ? <p className="mt-3 text-sm font-black text-[var(--color-text)]">No videos found.</p> : null}
      {!loading && !error ? (
        <div className="mt-4 grid w-full min-w-0 grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {videos.map((video) => (
            <article key={video.id} className="flex w-full min-w-0 flex-col overflow-hidden rounded-xl bg-[var(--color-surface)]">
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
          ))}
        </div>
      ) : null}
    </section>
  )
}

export default VideoList

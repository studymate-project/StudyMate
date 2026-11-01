import { getApiErrorMessage } from '../../api'
import { VideoGridSkeleton } from '../common/Skeletons'
import VideoCard from '../video/VideoCard'

function VideoList({ videos, loading, error }) {
  return (
    <section className="mt-7" aria-labelledby="explore-videos-heading">
      <h2 id="explore-videos-heading" className="text-sm font-black text-white">Videos</h2>
      {loading ? <VideoGridSkeleton /> : null}
      {!loading && error ? <p className="mt-3 text-sm font-black text-[var(--color-text)]">{getApiErrorMessage(error)}</p> : null}
      {!loading && !error && videos.length === 0 ? <p className="mt-3 text-sm font-black text-[var(--color-text)]">No videos found.</p> : null}
      {!loading && !error ? (
        <div className="mt-4 grid w-full min-w-0 grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {videos.map((video) => (
            <VideoCard key={video.id} video={video} />
          ))}
        </div>
      ) : null}
    </section>
  )
}

export default VideoList

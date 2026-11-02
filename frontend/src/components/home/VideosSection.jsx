import { useQuery } from '@tanstack/react-query'
import { getApiErrorMessage } from '../../api'
import { fetchVideoList } from '../../api/videos'
import { QUERY_STALE_TIMES } from '../../query/queryClient'
import { videoKeys } from '../../query/queryKeys'
import HorizontalScroller from '../common/HorizontalScroller'
import { VideoGridSkeleton } from '../common/Skeletons'
import VideoCard from '../video/VideoCard'

const VIDEO_PARAMS = { ordering: 'popular', page_size: 4 }

function VideosSection() {
  const query = useQuery({
    queryKey: videoKeys.list(VIDEO_PARAMS),
    queryFn: () => fetchVideoList(VIDEO_PARAMS),
    staleTime: QUERY_STALE_TIMES.lists,
  })
  const videos = query.data?.videos || []

  return (
    <section className="page-section">
      <div className="section-inner">
        <h2 className="section-title">Videos</h2>
        {/* <p className="section-copy">Learn from videos shared by StudyMate students</p> */}
        {query.isPending ? <VideoGridSkeleton horizontal /> : null}
        {!query.isPending && query.error && !videos.length ? <p className="mt-6 text-sm font-black text-[var(--color-text)]" role="alert">{getApiErrorMessage(query.error)}</p> : null}
        {!query.isPending && query.error && videos.length ? <p className="mt-6 text-sm text-[var(--color-text)]" role="alert">We couldn&apos;t refresh videos. Showing the latest available results.</p> : null}
        {!query.isPending && !query.error && !videos.length ? <p className="mt-6 text-sm text-[var(--color-text)]">No videos are available yet.</p> : null}
        {!query.isPending && videos.length ? (
          <HorizontalScroller className="mt-6" ariaLabel="videos">
            {videos.map((video) => <div key={video.id} className="w-[min(82vw,340px)] shrink-0 snap-start sm:w-[340px] lg:w-[360px]"><VideoCard video={video} /></div>)}
          </HorizontalScroller>
        ) : null}
      </div>
    </section>
  )
}

export default VideosSection

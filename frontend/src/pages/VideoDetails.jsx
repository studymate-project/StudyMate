import { Bookmark, Eye, MessageSquare, Share2, Star, ThumbsUp, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../api'
import { getVideoBySlug } from '../api/videos'
import Button from '../components/common/Button'
import YouTubePlayer from '../components/video/YouTubePlayer'

const formatNumber = (value) => Number(value).toLocaleString('en-IN')

const initialState = {
  video: null,
  loading: true,
  error: null,
  queryKey: null,
}

function VideoMessage({ title, message, showBackLink = true }) {
  return (
    <div className="mx-auto max-w-[900px] px-5 py-20 text-center">
      <h1 className="text-4xl font-black text-white">{title}</h1>
      <p className="mt-4 font-bold text-[var(--color-text)]">{message}</p>
      {showBackLink ? <Button to="/explore" className="mt-7">Back to Explore</Button> : null}
    </div>
  )
}

function VideoDetailsView({ slug }) {
  const queryKey = slug || ''
  const [state, setState] = useState(initialState)
  const [upvoted, setUpvoted] = useState(false)
  const [saved, setSaved] = useState(false)
  const [comments, setComments] = useState([])
  const [comment, setComment] = useState('')

  useEffect(() => {
    let isCurrent = true

    getVideoBySlug(queryKey).then(
      (video) => {
        if (isCurrent) setState({ video, loading: false, error: null, queryKey })
      },
      (error) => {
        if (isCurrent) setState({ video: null, loading: false, error, queryKey })
      },
    )

    return () => {
      isCurrent = false
    }
  }, [queryKey])

  const isCurrentQuery = state.queryKey === queryKey
  const loading = !isCurrentQuery || state.loading
  const video = isCurrentQuery ? state.video : null
  const error = isCurrentQuery ? state.error : null

  if (loading) return <VideoMessage title="Loading Video" message="Fetching the latest video details..." showBackLink={false} />
  if (error?.status === 404) return <VideoMessage title="Video Not Found" message="This video may have been moved or removed." />
  if (error) return <VideoMessage title="Unable to Load Video" message={getApiErrorMessage(error)} />
  if (!video) return <VideoMessage title="Video Not Found" message="This video may have been moved or removed." />

  const postComment = () => {
    if (!comment.trim()) return
    setComments((current) => [...current, { id: `comment-${Date.now()}`, body: comment.trim() }])
    setComment('')
  }

  const stats = [
    video.views != null ? { icon: Eye, value: `${formatNumber(video.views)} Views` } : null,
    video.rating != null ? { icon: Star, value: video.rating } : null,
    video.upvotes != null ? { icon: ThumbsUp, value: `${formatNumber(video.upvotes)} Upvotes` } : null,
  ].filter(Boolean)

  return (
    <div className="mx-auto w-full max-w-[1260px] px-5 py-6 sm:px-8 lg:px-10">
      <nav className="flex flex-wrap gap-2 text-sm font-black text-[var(--color-text)]" aria-label="Breadcrumb">
        <Link to="/">Home</Link><span>/</span><Link to="/explore">Explore</Link><span>/</span><Link to={`/explore?subject=${encodeURIComponent(video.subject.toLowerCase())}`}>{video.subject}</Link><span>/</span><span className="text-[var(--color-primary-light)]">{video.topic}</span>
      </nav>

      <div className="mt-5 grid gap-6 lg:grid-cols-[minmax(0,1fr)_330px]">
        <main className="min-w-0">
          <YouTubePlayer videoId={video.youtubeVideoId} title={video.title} />

          <section className="mt-7 border-b-2 border-[var(--color-border-strong)] pb-5">
            <h2 className="text-2xl font-black text-white">{video.title}</h2>
            <div className="mt-4 flex flex-wrap items-center gap-5 text-sm font-black text-[var(--color-text)]">
              {stats.map(({ icon: Icon, value }) => <span key={value} className="inline-flex items-center gap-2"><Icon size={16} className={Icon === Star ? 'fill-[var(--color-star)] text-[var(--color-star)]' : ''} />{value}</span>)}
              <span className="rounded-full bg-[#260777] px-3 py-1 text-white">{video.subject} to {video.topic}</span>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <Button onClick={() => setUpvoted((value) => !value)}><ThumbsUp size={18} />{upvoted ? 'Upvoted' : 'Upvote'}</Button>
              <Button variant="secondary" onClick={() => setSaved((value) => !value)}><Bookmark size={18} />{saved ? 'Saved' : 'Save'}</Button>
              <Button variant="dark"><Share2 size={18} />Share</Button>
            </div>
          </section>

          <section className="border-b-2 border-[var(--color-border-strong)] py-5">
            <h2 className="text-base font-black text-white">About this video</h2>
            <p className="mt-3 text-sm font-black leading-relaxed text-white/90">{video.description}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {video.tags.map((tag) => <span key={tag} className="rounded-full border-2 border-[var(--color-primary-light)] px-3 py-1 text-lg font-black text-[var(--color-primary-light)]">#{tag}</span>)}
            </div>
          </section>

          <section className="py-5">
            <h2 className="text-base font-black text-white">Discussion</h2>
            <div className="mt-3 space-y-3">
              {comments.map((item) => (
                <article key={item.id} className="bg-[var(--color-band)] p-4">
                  <div className="flex items-center gap-3"><Avatar /><h3 className="font-black text-white">You</h3></div>
                  <p className="mt-3 text-sm font-black text-white">"{item.body}"</p>
                  <div className="mt-3 flex gap-2"><Button variant="dark" className="min-h-8 px-3 text-sm"><ThumbsUp size={15} />Upvote</Button><Button variant="dark" className="min-h-8 px-3 text-sm"><MessageSquare size={15} />Reply</Button></div>
                </article>
              ))}
            </div>
            <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1fr)_180px]">
              <input value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Join the discussion..." className="h-12 border-2 border-[var(--color-border-strong)] bg-[var(--color-surface)] px-4 font-bold text-white outline-none focus:border-[var(--color-primary-light)]" />
              <Button onClick={postComment}>Post Comment</Button>
            </div>
          </section>
        </main>

        <aside className="space-y-5">
          <section className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5">
            <h2 className="text-sm font-black uppercase text-[var(--color-text)]">Uploaded By</h2>
            <div className="mt-4 flex items-center gap-4"><Avatar /><div>{video.author?.username ? <Link to={`/users/${video.author.username}`} className="font-black text-white">{video.author.name}</Link> : <p className="font-black text-white">{video.author?.name || 'StudyMate member'}</p>}<p className="text-sm font-black text-[var(--color-text)]">{video.uploadedAt || 'Date unavailable'}</p></div></div>
            {video.author?.username ? <Button to={`/users/${video.author.username}`} className="mt-5 w-full">View Profile</Button> : null}
          </section>
        </aside>
      </div>
    </div>
  )
}

function VideoDetails() {
  const { slug } = useParams()
  return <VideoDetailsView key={slug} slug={slug} />
}

function Avatar() {
  return <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#260777] text-[var(--color-primary-light)]"><UserRound size={21} /></span>
}

export default VideoDetails

import { Bookmark, Eye, Share2, ThumbsUp, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../api'
import { deleteVideoRating, getVideoBySlug, saveVideoRating } from '../api/videos'
import { getLoginState } from '../auth/navigation'
import { useAuth } from '../auth/useAuth'
import Button from '../components/common/Button'
import DiscussionPanel from '../components/common/DiscussionPanel'
import IconButton from '../components/common/IconButton'
import Rating from '../components/common/Rating'
import RatingControl from '../components/common/RatingControl'
import Spinner from '../components/common/Spinner'
import YouTubePlayer from '../components/video/YouTubePlayer'

const formatNumber = (value) => Number(value).toLocaleString('en-IN')

const initialState = {
  video: null,
  loading: true,
  error: null,
  queryKey: null,
}

function VideoMessage({ title, message, showBackLink = true, loadingLabel = '' }) {
  return (
    <div className="mx-auto flex max-w-[900px] justify-center px-5 py-20 text-center">
      {loadingLabel ? <Spinner label={loadingLabel} /> : <div><h1 className="text-4xl font-black text-white">{title}</h1><p className="mt-4 font-bold text-[var(--color-text)]">{message}</p>{showBackLink ? <Button to="/explore" className="mt-7">Back to Explore</Button> : null}</div>}
    </div>
  )
}

function ExpandableDescription({ description }) {
  const [expanded, setExpanded] = useState(false)
  const text = typeof description === 'string' ? description.trim() : ''

  return (
    <div>
      <p className={`mt-3 min-h-[2.75rem] text-sm font-black leading-relaxed text-white/90 ${text && !expanded ? 'line-clamp-2' : ''}`}>
        {text || 'No description available.'}
      </p>
      {text ? (
        <button
          type="button"
          aria-expanded={expanded}
          onClick={() => setExpanded((value) => !value)}
          className="mt-2 text-sm font-black text-[var(--color-primary-light)] underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
        >
          {expanded ? 'Less' : 'More'}
        </button>
      ) : null}
    </div>
  )
}

function VideoDetailsView({ slug }) {
  const queryKey = slug || ''
  const location = useLocation()
  const navigate = useNavigate()
  const { status: authStatus } = useAuth()
  const [state, setState] = useState(initialState)
  const [upvoted, setUpvoted] = useState(false)
  const [saved, setSaved] = useState(false)
  const [userRating, setUserRating] = useState(null)
  const [ratingState, setRatingState] = useState('idle')
  const [ratingError, setRatingError] = useState('')
  const [ratingNotice, setRatingNotice] = useState('')

  const requireAuth = () => {
    if (authStatus === 'authenticated') return true
    navigate('/login', { state: getLoginState(location) })
    return false
  }

  useEffect(() => {
    let isCurrent = true

    getVideoBySlug(queryKey).then(
      (video) => {
        if (isCurrent) {
          setState({ video, loading: false, error: null, queryKey })
          setUserRating(video.userRating ?? null)
        }
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

  const handleRatingChange = async (nextRating) => {
    if (authStatus !== 'authenticated') {
      setRatingNotice('Please sign in to submit a rating.')
      return
    }

    setRatingState('loading')
    setRatingError('')
    setRatingNotice('')
    try {
      await saveVideoRating(queryKey, nextRating)
      const refreshedVideo = await getVideoBySlug(queryKey)
      setState({ video: refreshedVideo, loading: false, error: null, queryKey })
      setUserRating(nextRating)
      setRatingNotice('Your rating was saved.')
    } catch (requestError) {
      setRatingError(getApiErrorMessage(requestError))
    } finally {
      setRatingState('idle')
    }
  }

  const handleRatingDelete = async () => {
    if (authStatus !== 'authenticated') {
      setRatingNotice('Please sign in to manage your rating.')
      return
    }

    setRatingState('loading')
    setRatingError('')
    setRatingNotice('')
    try {
      await deleteVideoRating(queryKey)
      const refreshedVideo = await getVideoBySlug(queryKey)
      setState({ video: refreshedVideo, loading: false, error: null, queryKey })
      setUserRating(null)
      setRatingNotice('Your rating was removed.')
    } catch (requestError) {
      setRatingError(getApiErrorMessage(requestError))
    } finally {
      setRatingState('idle')
    }
  }

  if (loading) return <VideoMessage loadingLabel="Loading video" showBackLink={false} />
  if (error?.status === 404) return <VideoMessage title="Video Not Found" message="This video may have been moved or removed." />
  if (error) return <VideoMessage title="Unable to Load Video" message={getApiErrorMessage(error)} />
  if (!video) return <VideoMessage title="Video Not Found" message="This video may have been moved or removed." />

  const stats = [
    video.views != null ? { icon: Eye, value: `${formatNumber(video.views)} Views` } : null,
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
            <h2 className="text-xl font-black text-white">{video.title}</h2>
            <div className="mt-4 flex flex-wrap items-center gap-5 text-sm font-black text-[var(--color-text)]">
              {stats.map(({ icon: Icon, value }) => <span key={value} className="inline-flex items-center gap-2"><Icon size={16} />{value}</span>)}
              <Rating value={video.rating} count={video.ratingCount} size={22} />
              <span className="rounded-lg bg-[var(--color-surface-muted)] px-3 py-1 text-[var(--color-text)]">{video.subject} to {video.topic}</span>
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-1" aria-label="Video actions">
              <IconButton
                label={upvoted ? 'Remove upvote from video' : 'Upvote video'}
                variant="default"
                onClick={() => { if (requireAuth()) setUpvoted((value) => !value) }}
                aria-pressed={upvoted}
                className={`h-11 w-11 rounded-full border-0 bg-transparent p-0 hover:border-transparent hover:bg-transparent ${upvoted ? 'text-[var(--color-primary-light)]' : ''}`}
              >
                <ThumbsUp size={20} className={upvoted ? 'fill-current' : ''} aria-hidden="true" />
              </IconButton>
              <IconButton
                label={saved ? 'Remove video from saved items' : 'Save video'}
                variant="default"
                onClick={() => { if (requireAuth()) setSaved((value) => !value) }}
                aria-pressed={saved}
                className={`h-11 w-11 rounded-full border-0 bg-transparent p-0 hover:border-transparent hover:bg-transparent ${saved ? 'text-[var(--color-primary-light)]' : ''}`}
              >
                <Bookmark size={20} className={saved ? 'fill-current' : ''} aria-hidden="true" />
              </IconButton>
              <IconButton
                label="Share video"
                variant="default"
                className="h-11 w-11 rounded-full border-0 bg-transparent p-0 hover:border-transparent hover:bg-transparent"
              >
                <Share2 size={20} aria-hidden="true" />
              </IconButton>
            </div>
          </section>

          <RatingControl
            key={`video-rating-${video.id}-${userRating ?? 'none'}`}
            itemLabel="video"
            value={userRating}
            authStatus={authStatus}
            isSaving={ratingState === 'loading'}
            error={ratingError}
            notice={ratingNotice}
            onSubmit={handleRatingChange}
            onDelete={handleRatingDelete}
          />

          <section className="border-b-2 border-[var(--color-border-strong)] py-5">
            <h2 className="text-base font-black text-white">About this video</h2>
            <ExpandableDescription description={video.description} />
            <div className="mt-5 flex flex-wrap gap-2">
              {video.tags.map((tag) => <span key={tag} className="rounded-full border-2 border-[var(--color-primary-light)] px-3 py-1 text-lg font-black text-[var(--color-primary-light)]">#{tag}</span>)}
            </div>
          </section>

          <DiscussionPanel itemLabel="this video" targetType="video" targetSlug={video.slug || queryKey} authStatus={authStatus} />
        </main>

        <aside className="space-y-5">
          <section className="p-5">
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
  return <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--color-surface-muted)] text-[var(--color-primary-light)]"><UserRound size={21} /></span>
}

export default VideoDetails

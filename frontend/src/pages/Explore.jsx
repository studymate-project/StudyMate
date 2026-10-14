import { useResourceList } from '../hooks/useResourceList'
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listVideos } from '../api/videos'
import ResourceList from '../components/explore/ResourceList'
import SubjectGrid from '../components/explore/SubjectGrid'
import VideoList from '../components/explore/VideoList'

const sortTabs = ['Most Popular', 'Latest', 'Top Rated', 'Most Downloaded']
const sortOrdering = {
  'Most Popular': 'popular',
  Latest: 'latest',
  'Top Rated': 'top_rated',
  'Most Downloaded': 'most_downloaded',
}

const contentTabs = [
  { label: 'File', value: 'file' },
  { label: 'Video', value: 'video' },
  { label: 'External Link', value: 'link' },
]

function filterVideos(videos = [], params = {}, activeSort) {
  const search = String(params.search || '').trim().toLowerCase()
  const subject = String(params.subject || '').trim().toLowerCase()
  const topic = String(params.topic || '').trim().toLowerCase()
  const academicLevel = String(params.academic_level || '').trim().toLowerCase()
  const uploader = String(params.uploader || '').trim()
  const tags = Array.isArray(params.tags) ? params.tags.map((tag) => String(tag).toLowerCase()) : []

  const filtered = (Array.isArray(videos) ? videos : []).filter((video) => {
    if (!video || typeof video !== 'object') return false

    const videoTags = Array.isArray(video.tags) ? video.tags.filter(Boolean) : []
    const searchableText = [
      video.title,
      video.description,
      video.subject,
      video.topic,
      video.course,
      video.semester,
      ...videoTags,
    ].join(' ').toLowerCase()
    const academicLevelValues = video.academicLevel && typeof video.academicLevel === 'object'
      ? [video.academicLevel.id, video.academicLevel.slug, video.academicLevel.name]
      : [video.academicLevel]

    return (!search || searchableText.includes(search))
      && (!subject || String(video.subject || '').toLowerCase() === subject)
      && (!topic || String(video.topic || '').toLowerCase() === topic)
      && (!academicLevel || academicLevelValues.filter(Boolean).some((value) => String(value).toLowerCase() === academicLevel))
      && (!uploader || String(video.author?.id || '') === uploader)
      && (!tags.length || tags.some((tag) => videoTags.some((videoTag) => String(videoTag).toLowerCase() === tag)))
  })

  if (activeSort === 'Top Rated') {
    return [...filtered].sort((left, right) => (right.rating ?? -1) - (left.rating ?? -1))
  }

  return filtered
}

function Explore() {
  const [activeSort, setActiveSort] = useState(sortTabs[0])
  const [searchParams, setSearchParams] = useSearchParams()
  const searchParamsKey = searchParams.toString()
  const requestedContent = searchParams.get('resource_type')
  const activeContent = contentTabs.some((tab) => tab.value === requestedContent) ? requestedContent : 'file'
  const requestParams = useMemo(() => {
    const currentSearchParams = new URLSearchParams(searchParamsKey)
    const params = {
      page: 1,
      page_size: 20,
      ordering: sortOrdering[activeSort],
      resource_type: activeContent,
    }

    for (const key of ['search', 'subject', 'topic', 'academic_level', 'difficulty', 'uploader']) {
      const value = currentSearchParams.get(key)
      if (value) params[key] = value
    }

    const tags = currentSearchParams.getAll('tags').filter(Boolean)
    if (tags.length) params.tags = tags

    return params
  }, [activeContent, activeSort, searchParamsKey])
  const resourceRequest = useResourceList(requestParams)
  const [videoState, setVideoState] = useState({ videos: [], loading: false, error: null, requestKey: null })

  const showVideos = activeContent === 'video'
  const videoRequestParams = useMemo(
    () => Object.fromEntries(Object.entries(requestParams).filter(([key]) => key !== 'resource_type')),
    [requestParams],
  )
  const videoRequestKey = JSON.stringify(videoRequestParams)

  useEffect(() => {
    if (!showVideos) return undefined

    let isCurrent = true
    listVideos(videoRequestParams).then(
      (result) => {
        if (isCurrent) setVideoState({ videos: filterVideos(result.videos, videoRequestParams, activeSort), loading: false, error: null, requestKey: videoRequestKey })
      },
      (error) => {
        if (isCurrent) setVideoState({ videos: [], loading: false, error, requestKey: videoRequestKey })
      },
    )

    return () => { isCurrent = false }
  }, [activeSort, showVideos, videoRequestKey, videoRequestParams])

  const videoLoading = showVideos && (videoState.loading || videoState.requestKey !== videoRequestKey)
  const videoError = showVideos && videoState.requestKey === videoRequestKey ? videoState.error : null

  return (
    <div className="mx-auto w-full max-w-[1260px]">
      <section className="min-w-0 px-5 py-8 sm:px-8 lg:px-10">
        <h1 className="text-3xl font-black text-white sm:text-4xl">Explore Study Resources</h1>

        <div className="mt-7 flex w-full max-w-xl items-center gap-2" role="tablist" aria-label="Content type">
          {contentTabs.map((tab) => {
            const isActive = activeContent === tab.value
            return (
              <button
                key={tab.value}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => {
                  const nextParams = new URLSearchParams(searchParams)
                  nextParams.set('resource_type', tab.value)
                  setSearchParams(nextParams)
                }}
                className={`relative min-h-11 min-w-0 flex-1 px-2 pb-3 pt-2 text-sm font-black transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)] sm:flex-none sm:px-3 sm:text-base ${isActive ? 'text-white after:absolute after:inset-x-2 after:bottom-0 after:h-0.5 after:rounded-full after:bg-[var(--color-primary-light)]' : 'text-[var(--color-text)] hover:text-white'}`}
              >
                {tab.label}
              </button>
            )
          })}
        </div>

        <div className="mt-7 flex flex-wrap gap-3" role="tablist" aria-label="Sort resources">
          {sortTabs.map((tab) => {
            const isActive = activeSort === tab
            return (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => setActiveSort(tab)}
                className={[
                  'min-h-12 border-2 px-5 text-base font-black transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]',
                  isActive
                    ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-primary-dark)]'
                    : 'border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text)] hover:bg-[var(--color-blue-hover)]',
                ].join(' ')}
              >
                {tab}
              </button>
            )
          })}
        </div>

        <SubjectGrid />
        {showVideos ? <VideoList videos={videoState.videos} loading={videoLoading} error={videoError} /> : <ResourceList resources={resourceRequest.resources} loading={resourceRequest.loading} error={resourceRequest.error} />}
      </section>
    </div>
  )
}

export default Explore

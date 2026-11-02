import { useMemo, useState } from 'react'
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import Button from '../components/common/Button'
import { ProfilePageSkeleton, Skeleton } from '../components/common/Skeletons'
import Footer from '../components/layout/Footer'
import ProfileHeader from '../components/profile/ProfileHeader'
import ProfileResources from '../components/profile/ProfileResources'
import { Achievements, RecentAnswers, RecentQuestions } from '../components/profile/ProfileSidebar'
import { getApiErrorMessage } from '../api/errors'
import {
  clearCurrentProfileCache,
  deleteResource,
  deleteVideo,
  getEducationSelection,
  listAnswersByAuthor,
  listQuestions,
  listResources,
  listSavedResources,
  listVideos,
  normalizeProfileResponse,
  normalizeProfileVideo,
  unsaveResource,
  updateProfile,
} from '../api'
import { QUERY_STALE_TIMES } from '../query/queryClient'
import { profileKeys } from '../query/queryKeys'
import { useAuth } from '../auth/useAuth'

const tabs = ['Resources', 'Questions', 'Answers', 'Saved Resources']
const PROFILE_PAGE_SIZE = 20

function getNextPageParam(lastPage) {
  const next = lastPage?.pagination?.next
  if (!next) return undefined

  const page = Number(new URL(next, window.location.origin).searchParams.get('page'))
  return Number.isInteger(page) && page > 0 ? page : undefined
}

function flattenPages(data, property) {
  return data?.pages?.flatMap((page) => page[property] || []) || []
}

function getQueryError(query) {
  return query.isError ? getApiErrorMessage(query.error) : ''
}

function StudentProfile() {
  const { user: currentUser, updateUser } = useAuth()
  const [activeTab, setActiveTab] = useState('Resources')
  const [avatarState, setAvatarState] = useState({ status: 'idle', error: '' })

  const userId = currentUser?.id || null
  const userKey = userId ? String(userId) : 'current'
  const queryEnabled = Boolean(userId)
  const educationQuery = useQuery({
    queryKey: profileKeys.currentSection(userKey, 'education'),
    queryFn: () => getEducationSelection(currentUser?.profile),
    enabled: queryEnabled,
    staleTime: QUERY_STALE_TIMES.profile,
  })
  const resourcesQuery = useInfiniteQuery({
    queryKey: profileKeys.currentSection(userKey, 'resources'),
    queryFn: ({ pageParam }) => listResources({ uploader: userId, page: pageParam, page_size: PROFILE_PAGE_SIZE }),
    initialPageParam: 1,
    getNextPageParam,
    enabled: queryEnabled,
    staleTime: QUERY_STALE_TIMES.profile,
  })
  const videosQuery = useInfiniteQuery({
    queryKey: profileKeys.currentSection(userKey, 'videos'),
    queryFn: ({ pageParam }) => listVideos({ uploader: userId, page: pageParam, page_size: PROFILE_PAGE_SIZE }),
    initialPageParam: 1,
    getNextPageParam,
    enabled: queryEnabled,
    staleTime: QUERY_STALE_TIMES.profile,
  })
  const questionsQuery = useInfiniteQuery({
    queryKey: profileKeys.currentSection(userKey, 'questions'),
    queryFn: ({ pageParam }) => listQuestions({ author: userId, page: pageParam, page_size: PROFILE_PAGE_SIZE }),
    initialPageParam: 1,
    getNextPageParam,
    enabled: queryEnabled,
    staleTime: QUERY_STALE_TIMES.profile,
  })
  const answersQuery = useInfiniteQuery({
    queryKey: profileKeys.currentSection(userKey, 'answers'),
    queryFn: ({ pageParam }) => listAnswersByAuthor(userId, { page: pageParam, page_size: PROFILE_PAGE_SIZE }),
    initialPageParam: 1,
    getNextPageParam,
    enabled: queryEnabled,
    staleTime: QUERY_STALE_TIMES.profile,
  })
  const savedQuery = useInfiniteQuery({
    queryKey: profileKeys.currentSection(userKey, 'saved'),
    queryFn: ({ pageParam }) => listSavedResources({ page: pageParam, page_size: PROFILE_PAGE_SIZE }),
    initialPageParam: 1,
    getNextPageParam,
    enabled: queryEnabled,
    staleTime: QUERY_STALE_TIMES.profile,
  })

  const resources = useMemo(() => flattenPages(resourcesQuery.data, 'resources').filter((resource) => resource.authorId === currentUser?.id), [resourcesQuery.data, currentUser?.id])
  const videos = useMemo(() => flattenPages(videosQuery.data, 'videos').filter((video) => video.author?.id === currentUser?.id), [videosQuery.data, currentUser?.id])
  const questions = useMemo(() => flattenPages(questionsQuery.data, 'questions'), [questionsQuery.data])
  const answers = useMemo(() => flattenPages(answersQuery.data, 'answers'), [answersQuery.data])
  const savedResources = useMemo(() => flattenPages(savedQuery.data, 'resources'), [savedQuery.data])
  const allResources = useMemo(() => resources.concat(videos.map(normalizeProfileVideo)).sort((first, second) => new Date(second.createdAt || 0).getTime() - new Date(first.createdAt || 0).getTime()), [resources, videos])

  const activityQueries = [resourcesQuery, videosQuery, questionsQuery, answersQuery, savedQuery]
  const activityStatus = activityQueries.some((query) => query.isError)
    ? 'error'
    : activityQueries.every((query) => query.isSuccess)
      ? 'ready'
      : 'loading'
  const activity = useMemo(() => ({
    loaded: activityStatus === 'ready',
    statsStatus: activityStatus,
    resources: allResources,
    questions,
    answers,
    savedResources,
    resourceCount: (resourcesQuery.data?.pages?.[0]?.pagination?.count || 0) + (videosQuery.data?.pages?.[0]?.pagination?.count || 0),
    questionCount: questionsQuery.data?.pages?.[0]?.pagination?.count || 0,
    answerCount: answersQuery.data?.pages?.[0]?.count || 0,
  }), [activityStatus, allResources, questions, answers, savedResources, resourcesQuery.data, videosQuery.data, questionsQuery.data, answersQuery.data])
  const profileData = useMemo(() => normalizeProfileResponse({ user: currentUser }, activity, educationQuery.data || {}), [currentUser, activity, educationQuery.data])

  const loadMoreResources = () => Promise.all([
    resourcesQuery.hasNextPage ? resourcesQuery.fetchNextPage() : null,
    videosQuery.hasNextPage ? videosQuery.fetchNextPage() : null,
  ])
  const loadMoreQuestions = () => questionsQuery.fetchNextPage()
  const loadMoreAnswers = () => answersQuery.fetchNextPage()
  const loadMoreSaved = () => savedQuery.fetchNextPage()

  const removeUploadedResource = async (resource) => {
    if (resource.targetType === 'video') await deleteVideo(resource.slug)
    else await deleteResource(resource.id)
    clearCurrentProfileCache()
  }

  const removeSavedResource = async (resource) => {
    await unsaveResource(resource.id)
    clearCurrentProfileCache()
  }

  const updateAvatar = async (avatarInput) => {
    if (!profileData.user?.username) return
    setAvatarState({ status: 'loading', error: '' })
    try {
      let payload = avatarInput
      if (avatarInput instanceof File) {
        payload = new FormData()
        payload.append('avatar_file', avatarInput)
      }
      const updatedProfile = await updateProfile(profileData.user.username, payload)
      const nextAvatarUrl = updatedProfile.avatar_url || null
      updateUser({
        ...currentUser,
        profile: { ...currentUser.profile, avatar_url: nextAvatarUrl || '' },
      })
      setAvatarState({ status: 'idle', error: '' })
    } catch (error) {
      setAvatarState({ status: 'error', error: getApiErrorMessage(error) })
      throw error
    }
  }

  if (!currentUser) return <ProfilePageSkeleton />

  const resourcesError = [resourcesQuery, videosQuery].map(getQueryError).filter(Boolean).join(' ')
  const questionsError = getQueryError(questionsQuery)
  const answersError = getQueryError(answersQuery)
  const savedError = getQueryError(savedQuery)
  const tabContent = activeTab === 'Resources'
    ? <ProfileResources
      resources={allResources}
      loading={resourcesQuery.isPending || videosQuery.isPending}
      errorMessage={resourcesError}
      onRetry={() => { void resourcesQuery.refetch(); void videosQuery.refetch() }}
      hasMore={resourcesQuery.hasNextPage || videosQuery.hasNextPage}
      loadingMore={resourcesQuery.isFetchingNextPage || videosQuery.isFetchingNextPage}
      onLoadMore={loadMoreResources}
      onDelete={removeUploadedResource}
    />
    : activeTab === 'Questions'
      ? <RecentQuestions
        questions={questions.map((question) => ({ questionId: question.id, slug: question.slug, title: question.title, votes: question.upvotes ?? 0, answers: question.answerCount ?? 0 }))}
        loading={questionsQuery.isPending}
        errorMessage={questionsError}
        onRetry={() => { void questionsQuery.refetch() }}
        hasMore={questionsQuery.hasNextPage}
        loadingMore={questionsQuery.isFetchingNextPage}
        onLoadMore={loadMoreQuestions}
      />
      : activeTab === 'Answers'
        ? <RecentAnswers answers={answers} loading={answersQuery.isPending} errorMessage={answersError} onRetry={() => { void answersQuery.refetch() }} hasMore={answersQuery.hasNextPage} loadingMore={answersQuery.isFetchingNextPage} onLoadMore={loadMoreAnswers} />
        : <ProfileResources resources={savedResources} title="Saved resources" empty="No saved resources yet. Explore resources and save the ones you want to revisit." loading={savedQuery.isPending} errorMessage={savedError} onRetry={() => { void savedQuery.refetch() }} hasMore={savedQuery.hasNextPage} loadingMore={savedQuery.isFetchingNextPage} onLoadMore={loadMoreSaved} onUnsave={removeSavedResource} />

  return <><ProfileHeader user={profileData.user} profile={profileData.profile} editable avatarBusy={avatarState.status === 'loading'} avatarError={avatarState.error} onAvatarFile={updateAvatar} onAvatarUrl={updateAvatar} action={<Button to="/profile/edit" variant="secondary" className="min-h-9 px-4 text-sm">Edit Profile</Button>} /><main className="mx-auto min-h-[calc(100svh-26rem)] w-full max-w-[1260px] px-5 py-7 sm:px-8 lg:px-10"><ProfileDetails profile={profileData.profile} loading={educationQuery.isPending} errorMessage={educationQuery.isError ? getApiErrorMessage(educationQuery.error) : ''} onRetry={() => { void educationQuery.refetch() }} /><div className="mt-7 overflow-x-auto border-b border-[var(--color-border)]"><div className="flex min-w-max justify-between gap-7" role="tablist" aria-label="Profile content">{tabs.map((tab) => <button key={tab} type="button" role="tab" aria-selected={activeTab === tab} onClick={() => setActiveTab(tab)} className={`min-h-12 border-b-[3px] px-2 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] ${activeTab === tab ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)] text-[var(--color-primary-light)]' : 'border-transparent text-[var(--color-text)] hover:text-white'}`}>{tab}</button>)}</div></div><div className="mt-6 grid gap-7 lg:grid-cols-[minmax(0,1.7fr)_minmax(280px,0.9fr)]"><section>{tabContent}</section><aside className="space-y-6"><Achievements achievements={profileData.profile.achievements} /><RecentQuestions questions={profileData.profile.recentQuestions} loading={questionsQuery.isPending} errorMessage={questionsError} onRetry={() => { void questionsQuery.refetch() }} showLoadMore={false} /></aside></div></main><Footer /></>
}

function ProfileDetails({ profile, loading, errorMessage, onRetry }) {
  const background = profile.customBackground || profile.educationBackground?.name
  const course = profile.customCourse || profile.course?.name
  const stage = profile.academicLevel?.name || profile.academicLevelValue
  const location = [profile.city, profile.state, profile.country].filter(Boolean).join(', ')
  const details = [['Location', location], ['Educational background', background], ['Course / program', course], ['Academic level / stage', stage]].filter(([, value]) => value)

  if (!loading && !errorMessage && !details.length) return null
  return <section className="grid gap-3 p-5 sm:grid-cols-2 sm:p-6" aria-label="Education and location">{errorMessage ? <div className="sm:col-span-2 border border-[var(--color-danger)] p-3 text-sm text-[var(--color-danger)]" role="alert"><p>{errorMessage}</p><button type="button" onClick={onRetry} className="mt-2 font-semibold underline">Try again</button></div> : null}{loading && !details.length ? Array.from({ length: 4 }, (_, index) => <div key={index}><Skeleton className="h-3 w-36" /><Skeleton className="mt-2 h-5 w-44" /></div>) : details.map(([label, value]) => <div key={label}><p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text)]">{label}</p><p className="mt-1 text-sm font-semibold text-white">{value}</p></div>)}</section>
}

export default StudentProfile

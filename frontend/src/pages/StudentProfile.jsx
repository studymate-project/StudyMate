import { useEffect, useState } from 'react'
import Button from '../components/common/Button'
import Spinner from '../components/common/Spinner'
import Footer from '../components/layout/Footer'
import ProfileHeader from '../components/profile/ProfileHeader'
import ProfileResources from '../components/profile/ProfileResources'
import { Achievements, RecentAnswers, RecentQuestions } from '../components/profile/ProfileSidebar'
import { getApiErrorMessage } from '../api/errors'
import { clearCurrentProfileCache, deleteResource, deleteVideo, getCurrentProfile, unsaveResource, updateProfile } from '../api'
import { useAuth } from '../auth/useAuth'

const tabs = ['Resources', 'Questions', 'Answers', 'Saved Resources']

function StudentProfile() {
  const { user: currentUser, updateUser } = useAuth()
  const [activeTab, setActiveTab] = useState('Resources')
  const [profileState, setProfileState] = useState({ status: 'loading', data: null, error: null })
  const [reloadKey, setReloadKey] = useState(0)
  const [avatarState, setAvatarState] = useState({ status: 'idle', error: '' })

  const removeUploadedResource = async (resource) => {
    if (resource.targetType === 'video') await deleteVideo(resource.slug)
    else await deleteResource(resource.id)
    clearCurrentProfileCache()
    setProfileState((current) => current.data
      ? { ...current, data: { ...current.data, profile: { ...current.data.profile, resources: current.data.profile.resources.filter((item) => !(item.id === resource.id && item.targetType === resource.targetType)) } } }
      : current)
  }

  const removeSavedResource = async (resource) => {
    await unsaveResource(resource.id)
    clearCurrentProfileCache()
    setProfileState((current) => current.data
      ? { ...current, data: { ...current.data, profile: { ...current.data.profile, savedResources: current.data.profile.savedResources.filter((item) => item.id !== resource.id) } } }
      : current)
  }

  useEffect(() => {
    let isActive = true

    if (!currentUser) return undefined

    getCurrentProfile(currentUser).then(
      (data) => {
        if (isActive) setProfileState({ status: 'success', data, error: null })
      },
      (error) => {
        if (isActive) setProfileState({ status: 'error', data: null, error })
      },
    )

    return () => { isActive = false }
  }, [currentUser, reloadKey])

  const updateAvatar = async (avatarInput) => {
    if (!profileState.data?.user?.username) return
    setAvatarState({ status: 'loading', error: '' })
    try {
      let payload = avatarInput
      if (avatarInput instanceof File) {
        payload = new FormData()
        payload.append('avatar_file', avatarInput)
      }
      const updatedProfile = await updateProfile(profileState.data.user.username, payload)
      const nextAvatarUrl = updatedProfile.avatar_url || null
      setProfileState((current) => current.data
        ? {
          ...current,
          data: {
            ...current.data,
            user: { ...current.data.user, avatarUrl: nextAvatarUrl },
            profile: { ...current.data.profile, avatarUrl: nextAvatarUrl || '' },
          },
        }
        : current)
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

  if (profileState.status === 'loading') {
    return <ProfilePageState loadingLabel="Loading profile" />
  }

  if (profileState.status === 'error') {
    const isUnauthenticated = profileState.error?.status === 401
    return <ProfilePageState
      title={isUnauthenticated ? 'Sign in required' : 'Unable to load profile'}
      message={isUnauthenticated ? 'Sign in to view your profile.' : getApiErrorMessage(profileState.error)}
      action={isUnauthenticated
        ? <Button to="/login" variant="secondary" className="mt-5">Sign in</Button>
        : <button type="button" onClick={() => { setProfileState({ status: 'loading', data: null, error: null }); setReloadKey((key) => key + 1) }} className="mt-5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-5 py-2 text-sm font-semibold text-[var(--color-text)] hover:bg-[var(--color-blue-hover)]">Try again</button>}
    />
  }

  const { user, profile } = profileState.data
  const tabContent = activeTab === 'Resources'
    ? <ProfileResources resources={profile.resources} onDelete={removeUploadedResource} />
    : activeTab === 'Questions'
      ? <RecentQuestions questions={profile.recentQuestions} />
      : activeTab === 'Answers'
        ? <RecentAnswers answers={profile.recentAnswers} />
        : <ProfileResources resources={profile.savedResources} title="Saved resources" empty="No saved resources yet. Explore resources and save the ones you want to revisit." onUnsave={removeSavedResource} />

  return <><ProfileHeader user={user} profile={profile} editable avatarBusy={avatarState.status === 'loading'} avatarError={avatarState.error} onAvatarFile={updateAvatar} onAvatarUrl={updateAvatar} action={<Button to="/profile/edit" variant="secondary" className="min-h-9 px-4 text-sm">Edit Profile</Button>} /><main className="mx-auto min-h-[calc(100svh-26rem)] w-full max-w-[1260px] px-5 py-7 sm:px-8 lg:px-10"><ProfileDetails profile={profile} /><div className="mt-7 overflow-x-auto border-b border-[var(--color-border)]"><div className="flex min-w-max justify-between gap-7" role="tablist" aria-label="Profile content">{tabs.map((tab) => <button key={tab} type="button" role="tab" aria-selected={activeTab === tab} onClick={() => setActiveTab(tab)} className={`min-h-12 border-b-[3px] px-2 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] ${activeTab === tab ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)] text-[var(--color-primary-light)]' : 'border-transparent text-[var(--color-text)] hover:text-white'}`}>{tab}</button>)}</div></div><div className="mt-6 grid gap-7 lg:grid-cols-[minmax(0,1.7fr)_minmax(280px,0.9fr)]"><section>{tabContent}</section><aside className="space-y-6"><Achievements achievements={profile.achievements} /><RecentQuestions questions={profile.recentQuestions} /></aside></div></main><Footer /></>
}

function ProfileDetails({ profile }) {
  const background = profile.customBackground || profile.educationBackground?.name
  const course = profile.customCourse || profile.course?.name
  const stage = profile.academicLevel?.name || profile.academicLevelValue
  const location = [profile.city, profile.state, profile.country].filter(Boolean).join(', ')
  const details = [
    ['Location', location],
    ['Educational background', background],
    ['Course / program', course],
    ['Academic level / stage', stage],
  ].filter(([, value]) => value)

  if (!details.length) return null
  return <section className="grid gap-3 p-5 sm:grid-cols-2 sm:p-6" aria-label="Education and location">
    {details.map(([label, value]) => <div key={label}><p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text)]">{label}</p><p className="mt-1 text-sm font-semibold text-white">{value}</p></div>)}
  </section>
}

function ProfilePageState({ title, message, action = null, loadingLabel = '' }) {
  return <><main className="mx-auto flex min-h-[calc(100svh-13rem)] w-full max-w-[1260px] items-center justify-center px-5 py-12 sm:px-8 lg:px-10"><section className="flex w-full max-w-xl items-center justify-center border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-7 text-center">{loadingLabel ? <Spinner label={loadingLabel} /> : <div><h1 className="text-xl font-semibold text-white">{title}</h1><p className="mt-2 text-sm text-[var(--color-text)]">{message}</p>{action}</div>}</section></main><Footer /></>
}

export default StudentProfile

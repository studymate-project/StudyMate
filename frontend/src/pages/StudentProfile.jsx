import { useEffect, useState } from 'react'
import Button from '../components/common/Button'
import Spinner from '../components/common/Spinner'
import Footer from '../components/layout/Footer'
import ProfileHeader from '../components/profile/ProfileHeader'
import ProfileResources from '../components/profile/ProfileResources'
import { Achievements, RecentAnswers, RecentQuestions } from '../components/profile/ProfileSidebar'
import { getApiErrorMessage } from '../api/errors'
import { getCurrentProfile, updateProfile } from '../api/profile'

const tabs = ['Resources', 'Questions', 'Answers', 'Saved Resources']

function StudentProfile() {
  const [activeTab, setActiveTab] = useState('Resources')
  const [profileState, setProfileState] = useState({ status: 'loading', data: null, error: null })
  const [reloadKey, setReloadKey] = useState(0)
  const [avatarState, setAvatarState] = useState({ status: 'idle', error: '' })

  useEffect(() => {
    let isActive = true

    getCurrentProfile().then(
      (data) => {
        if (isActive) setProfileState({ status: 'success', data, error: null })
      },
      (error) => {
        if (isActive) setProfileState({ status: 'error', data: null, error })
      },
    )

    return () => { isActive = false }
  }, [reloadKey])

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
        : <button type="button" onClick={() => { setProfileState({ status: 'loading', data: null, error: null }); setReloadKey((key) => key + 1) }} className="mt-5 border border-[#2585c0] px-5 py-2 text-sm font-semibold text-[#55b7ee] hover:bg-[#073c68]">Try again</button>}
    />
  }

  const { user, profile } = profileState.data
  const tabContent = activeTab === 'Resources'
    ? <ProfileResources resources={profile.resources} />
    : activeTab === 'Questions'
      ? <RecentQuestions questions={profile.recentQuestions} />
      : activeTab === 'Answers'
        ? <RecentAnswers answers={profile.recentAnswers} />
        : <ProfileResources resources={profile.savedResources} title="Saved resources" empty="No saved resources yet." />

  return <><ProfileHeader user={user} profile={profile} editable avatarBusy={avatarState.status === 'loading'} avatarError={avatarState.error} onAvatarFile={updateAvatar} onAvatarUrl={updateAvatar} action={<Button to="/profile/edit" variant="secondary" className="min-h-9 px-4 text-sm">Edit Profile</Button>} /><main className="mx-auto min-h-[calc(100svh-26rem)] w-full max-w-[1260px] px-5 py-7 sm:px-8 lg:px-10"><div className="overflow-x-auto border-b border-[var(--color-border)]"><div className="flex min-w-max justify-between gap-7" role="tablist" aria-label="Profile content">{tabs.map((tab) => <button key={tab} type="button" role="tab" aria-selected={activeTab === tab} onClick={() => setActiveTab(tab)} className={`min-h-12 border-b-[3px] px-2 text-sm font-semibold ${activeTab === tab ? 'border-[#55b7ee] text-[#55b7ee]' : 'border-transparent text-[var(--color-text)] hover:text-white'}`}>{tab}</button>)}</div></div><div className="mt-6 grid gap-7 lg:grid-cols-[minmax(0,1.7fr)_minmax(280px,0.9fr)]"><section>{tabContent}</section><aside className="space-y-6"><Achievements achievements={profile.achievements} /><RecentQuestions questions={profile.recentQuestions} /></aside></div></main><Footer /></>
}

function ProfilePageState({ title, message, action = null, loadingLabel = '' }) {
  return <><main className="mx-auto flex min-h-[calc(100svh-13rem)] w-full max-w-[1260px] items-center justify-center px-5 py-12 sm:px-8 lg:px-10"><section className="flex w-full max-w-xl items-center justify-center border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-7 text-center">{loadingLabel ? <Spinner label={loadingLabel} /> : <div><h1 className="text-xl font-semibold text-white">{title}</h1><p className="mt-2 text-sm text-[var(--color-text)]">{message}</p>{action}</div>}</section></main><Footer /></>
}

export default StudentProfile

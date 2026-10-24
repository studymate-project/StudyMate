import { BookOpen, MessageSquare, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { followProfile, getApiErrorMessage, getPublicProfile, listQuestions, listResources, unfollowProfile } from '../api'
import Button from '../components/common/Button'
import Spinner from '../components/common/Spinner'
import { useAuth } from '../auth/useAuth'

const initialState = { status: 'loading', queryKey: null, user: null, profile: null, resources: [], questions: [], error: null }

function UserProfile() {
  const { username } = useParams()
  const { status: authStatus, user: currentUser } = useAuth()
  const [state, setState] = useState(initialState)
  const [followStatus, setFollowStatus] = useState('idle')
  const [followError, setFollowError] = useState('')

  useEffect(() => {
    let active = true

    getPublicProfile(username).then(async (profileResult) => {
      const profileUserId = profileResult.user.id
      const [resourceResult, questionResult] = await Promise.all([
        listResources(profileUserId ? { uploader: profileUserId, page_size: 20 } : {}),
        listQuestions(profileUserId ? { author: profileUserId, page_size: 20 } : {}),
      ])
      return [profileResult, resourceResult, questionResult]
    }).then(
      ([profileResult, resourceResult, questionResult]) => {
        if (!active) return
        const profileUsername = profileResult.user.username || username
        const matchesUsername = (value) => value?.toLowerCase() === profileUsername.toLowerCase()
        const resources = resourceResult.resources.filter((resource) => matchesUsername(resource.author?.username))
        const questions = questionResult.questions.filter((question) => matchesUsername(question.author?.username))
        setState({
          status: 'success',
          queryKey: profileUsername,
          user: profileResult.user,
          profile: profileResult.profile,
          resources,
          questions,
          error: null,
        })
      },
      (error) => {
        if (active) setState({ ...initialState, status: 'error', queryKey: username, error })
      },
    )

    return () => { active = false }
  }, [username])

  const isCurrentProfile = state.queryKey?.toLowerCase() === username?.toLowerCase()
  if (!isCurrentProfile || state.status === 'loading') return <ProfileMessage loadingLabel="Loading profile" showBackLink={false} />
  if (state.status === 'error') return <ProfileMessage title={state.error?.status === 404 ? 'User Not Found' : 'Unable to Load Profile'} message={state.error?.status === 404 ? 'This profile may have been moved or removed.' : getApiErrorMessage(state.error)} />

  const { user, profile, resources, questions } = state
  const canFollow = authStatus === 'authenticated'
    && currentUser?.username?.toLowerCase() !== user.username?.toLowerCase()

  const handleFollow = async () => {
    if (!canFollow || followStatus === 'loading') return
    const nextFollowing = !profile.isFollowing
    setFollowStatus('loading')
    setFollowError('')
    try {
      await (nextFollowing ? followProfile : unfollowProfile)(user.username)
      setState((current) => ({
        ...current,
        profile: { ...current.profile, isFollowing: nextFollowing },
      }))
    } catch (error) {
      setFollowError(getApiErrorMessage(error))
    } finally {
      setFollowStatus('idle')
    }
  }

  return (
    <div className="mx-auto w-full max-w-[1260px] px-5 py-8 sm:px-8 lg:px-10">
      <section className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-6">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
          <span className="flex h-20 w-20 items-center justify-center rounded-full bg-[var(--color-primary-dark)] text-[var(--color-primary-light)]"><UserRound size={40} /></span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <h1 className="text-4xl font-black text-white">{user.name}</h1>
              {canFollow ? <Button type="button" variant="secondary" disabled={followStatus === 'loading'} onClick={handleFollow}>{followStatus === 'loading' ? 'Saving...' : profile.isFollowing ? 'Following' : 'Follow'}</Button> : null}
            </div>
            <p className="mt-2 font-black text-[var(--color-text)]">@{user.username}{profile.college ? ` - ${profile.college}` : ''}</p>
            {profile.bio ? <p className="mt-3 max-w-2xl text-sm font-bold text-[var(--color-text)]">{profile.bio}</p> : null}
            {followError ? <p className="mt-3 text-sm text-[var(--color-danger)]" role="alert">{followError}</p> : null}
          </div>
        </div>
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat value={resources.length} label="Resources Shared" />
          <Stat value={profile.contributionPoints} label="Points" />
          <Stat value={questions.length} label="Questions" />
          <Stat value="-" label="Answers" />
        </div>
      </section>

      <div className="mt-7 grid gap-7 lg:grid-cols-2">
        <ProfileList title="Resources Uploaded" empty="No resources uploaded yet.">
          {resources.map((resource) => <Link key={resource.id} to={`/resources/${resource.slug}`} className="flex items-center gap-3 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4"><BookOpen className="shrink-0 text-[var(--color-text)]" /><span className="min-w-0"><strong className="block truncate text-white">{resource.title}</strong><span className="text-sm font-black text-[var(--color-text)]">{resource.type}</span></span></Link>)}
        </ProfileList>
        <ProfileList title="Questions Asked" empty="No questions asked yet.">
          {questions.map((question) => <Link key={question.id} to={`/questions/${question.slug}`} className="flex items-center gap-3 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4"><MessageSquare className="shrink-0 text-[var(--color-primary-light)]" /><span className="min-w-0"><strong className="block text-white">{question.title}</strong><span className="text-sm font-black text-[var(--color-text)]">{question.upvotes ?? 0} Upvotes - {question.answerCount} Answers</span></span></Link>)}
        </ProfileList>
      </div>
    </div>
  )
}

function ProfileMessage({ title, message, showBackLink = true, loadingLabel = '' }) {
  return <div className="mx-auto flex max-w-[900px] justify-center px-5 py-20 text-center">{loadingLabel ? <Spinner label={loadingLabel} /> : <div><h1 className="text-4xl font-black text-white">{title}</h1><p className="mt-4 font-bold text-[var(--color-text)]">{message}</p>{showBackLink ? <Button to="/community" className="mt-7">Back to Community</Button> : null}</div>}</div>
}

function ProfileList({ title, empty, children }) {
  return <section><h2 className="text-xl font-black text-white">{title}</h2><div className="mt-3 space-y-3">{children.length ? children : <p className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-sm font-black text-[var(--color-text)]">{empty}</p>}</div></section>
}

function Stat({ value, label }) {
  return <article className="bg-[var(--color-band)] p-4 text-center"><p className="text-2xl font-black text-white">{value}</p><p className="mt-2 text-sm font-black text-[var(--color-text)]">{label}</p></article>
}

export default UserProfile

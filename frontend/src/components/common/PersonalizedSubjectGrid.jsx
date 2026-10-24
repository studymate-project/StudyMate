import { Link } from 'react-router-dom'
import { getApiErrorMessage } from '../../api/errors'
import { useAuth } from '../../auth/useAuth'
import SubjectCard from '../home/SubjectCard'
import usePersonalizedSubjects from '../../hooks/usePersonalizedSubjects'
import Spinner from './Spinner'

function PersonalizedSubjectGrid({ compact = false }) {
  const { status: authStatus } = useAuth()
  const { error, isProfileComplete, loading, subjects } = usePersonalizedSubjects()

  if (loading) {
    return <div className="flex min-h-24 items-center justify-center"><Spinner label="Loading personalized subjects" /></div>
  }

  if (authStatus === 'unauthenticated') {
    return <p className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-5 text-sm text-[var(--color-text)]">Sign in to see subjects matched to your interests and educational background. <Link className="font-semibold text-[var(--color-primary-light)] underline underline-offset-4" to="/login">Sign in</Link></p>
  }

  if (error) {
    return <p className="rounded-xl border border-[var(--color-danger)] bg-[var(--color-surface)] px-4 py-5 text-sm text-[var(--color-danger)]" role="alert">{getApiErrorMessage(error)}</p>
  }

  return <>
    {!isProfileComplete ? <p className="mb-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 text-sm text-[var(--color-text)]">Complete your educational profile to refine these subjects. <Link className="font-semibold text-[var(--color-primary-light)] underline underline-offset-4" to="/onboarding">Complete profile</Link></p> : null}
    {/* {isProfileComplete && !hasSelectedInterests ? <p className="mb-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-band)] px-4 py-3 text-sm text-[var(--color-text)]">Your course and academic level shape these subjects. Add interests to refine your recommendations.</p> : null} */}
    {subjects.length ? <div className={`grid grid-cols-1 gap-5 sm:grid-cols-2 ${compact ? 'lg:grid-cols-3' : 'lg:grid-cols-3 xl:grid-cols-6'}`}>
      {subjects.map((subject) => <SubjectCard key={subject.slug} subject={subject} compact={compact} />)}
    </div> : <p className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-5 text-sm text-[var(--color-text)]">No subjects are available yet. Try again after more resources are added.</p>}
  </>
}

export default PersonalizedSubjectGrid

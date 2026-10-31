import { UserRound } from 'lucide-react'
import Button from '../common/Button'

function UploaderCard({ user = {} }) {
  const academicDetails = [user.course, user.semester].filter(Boolean).join(' - ')
  const contributionDetails = [
    user.resourcesShared ? `${user.resourcesShared} Resources Shared` : null,
    user.points ? `${user.points} Points` : null,
  ].filter(Boolean).join(' - ')

  return (
    <aside className="p-5">
      <h2 className="text-base font-black text-white">About the Uploader</h2>
      <div className="mt-4 h-px bg-[var(--color-border-strong)]" />
      <div className="mt-5 flex items-center gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[var(--color-primary-dark)] text-[var(--color-primary-light)]">
          <UserRound size={24} />
        </div>
        <div className="min-w-0">
          <h3 className="text-base font-black text-white">{user.name || 'StudyMate member'}</h3>
          <p className="text-sm font-black text-[var(--color-text)]">
            {academicDetails || 'Community contributor'}
          </p>
        </div>
      </div>
      {contributionDetails ? <p className="mt-5 text-sm font-black text-[var(--color-text)]">{contributionDetails}</p> : null}
      <Button to={user.username ? `/users/${encodeURIComponent(user.username)}` : undefined} variant="secondary" className="mt-4 w-full">
        View Profile
      </Button>
    </aside>
  )
}

export default UploaderCard

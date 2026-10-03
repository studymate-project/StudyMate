import { Link } from 'react-router-dom'

function AuthHeader({ actionLabel, actionTo }) {
  return (
    <header className="border-b border-[var(--color-border)] bg-[var(--color-nav)]">
      <div className="flex min-h-16 w-full items-center justify-between px-5 sm:px-10">
        <Link
          to="/"
          className="text-base font-semibold tracking-wide text-[var(--color-primary-light)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--color-primary-light)]"
        >
          StudyMate
        </Link>
        <Link
          to={actionTo}
          className="border border-[var(--color-primary-light)] px-4 py-2 text-sm font-medium text-[var(--color-primary-light)] transition-colors hover:bg-[var(--color-primary-soft)] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
        >
          {actionLabel}
        </Link>
      </div>
    </header>
  )
}

export default AuthHeader

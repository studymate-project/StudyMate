import { Link } from 'react-router-dom'
import Rating from './Rating'

function RatingControl({
  itemLabel,
  value,
  authStatus,
  isSaving,
  error,
  notice,
  onChange,
  onDelete,
}) {
  const isAuthenticated = authStatus === 'authenticated'

  return (
    <section className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5" aria-labelledby={`${itemLabel}-rating-title`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 id={`${itemLabel}-rating-title`} className="text-base font-black text-white">Rate this {itemLabel}</h2>
          <p className="mt-2 text-sm font-bold text-[var(--color-text)]">
            {isAuthenticated ? 'Choose one to rate or update your rating.' : 'Sign in to rate this item.'}
          </p>
        </div>
        <Rating
          value={value}
          interactive
          showValue={false}
          showCount={false}
          onChange={onChange}
          disabled={isSaving}
          className="text-lg"
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-4 text-sm font-bold">
        <span className="text-[var(--color-text)]">
          {value ? `Your rating: ${value}/5` : 'No rating selected'}
        </span>
        {isAuthenticated && value != null ? (
          <button
            type="button"
            onClick={onDelete}
            disabled={isSaving}
            className="text-[var(--color-primary-light)] underline decoration-1 underline-offset-4 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSaving ? 'Saving...' : 'Remove my rating'}
          </button>
        ) : !isAuthenticated ? (
          <Link to="/login" className="text-[var(--color-primary-light)] underline decoration-1 underline-offset-4">
            Sign in to rate
          </Link>
        ) : null}
      </div>

      {notice ? <p role="status" className="mt-3 text-sm font-bold text-[var(--color-primary-light)]">{notice}</p> : null}
      {error ? <p role="alert" className="mt-3 text-sm font-bold text-[#ffadb6]">{error}</p> : null}
    </section>
  )
}

export default RatingControl

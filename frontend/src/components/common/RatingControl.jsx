import { useState } from 'react'
import { Link } from 'react-router-dom'
import Rating from './Rating'

function RatingControl({
  itemLabel,
  value,
  authStatus,
  isSaving,
  error,
  notice,
  onSubmit,
  onDelete,
}) {
  const isAuthenticated = authStatus === 'authenticated'
  const [selectedRating, setSelectedRating] = useState(value ?? null)

  const submitRating = () => {
    if (!isAuthenticated || selectedRating == null || isSaving) return
    onSubmit(selectedRating)
  }

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
          value={selectedRating}
          interactive
          showValue={false}
          showCount={false}
          onChange={setSelectedRating}
          disabled={!isAuthenticated || isSaving}
          size={24}
          className="text-lg"
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-4 text-sm font-bold">
        <span className="text-[var(--color-text)]">
          {selectedRating ? `Selected rating: ${selectedRating}/5` : 'No rating selected'}
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

      {isAuthenticated ? (
        <button
          type="button"
          onClick={submitRating}
          disabled={isSaving || selectedRating == null}
          className="mt-4 inline-flex min-h-10 items-center rounded-lg border border-[var(--color-primary)] bg-[var(--color-primary)] px-4 text-sm font-black text-[var(--color-primary-dark)] transition-colors hover:bg-[var(--color-primary-hover)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSaving ? 'Submitting...' : 'Submit rating'}
        </button>
      ) : null}

      {notice ? <p role="status" className="mt-3 text-sm font-bold text-[var(--color-primary-light)]">{notice}</p> : null}
      {error ? <p role="alert" className="mt-3 text-sm font-bold text-[var(--color-danger)]">{error}</p> : null}
    </section>
  )
}

export default RatingControl

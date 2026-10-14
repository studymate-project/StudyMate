import { Star } from 'lucide-react'

function clampFill(value, index) {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return 0
  return Math.min(1, Math.max(0, numericValue - index))
}

function RatingStar({ fill, size = 20, label, onClick, disabled }) {
  const star = (
    <span className="relative inline-flex" aria-hidden="true">
      <Star size={size} className="text-[var(--color-star)]" />
      {fill > 0 ? (
        <span className="absolute inset-y-0 left-0 overflow-hidden" style={{ width: `${fill * 100}%` }}>
          <Star size={size} className="fill-[var(--color-star)] text-[var(--color-star)]" />
        </span>
      ) : null}
    </span>
  )

  if (!onClick) return star

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className="rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {star}
    </button>
  )
}

function formatRating(value) {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return null
  return numericValue.toFixed(1)
}

function Rating({
  value,
  count,
  stars = 5,
  showValue = true,
  showCount = true,
  interactive = false,
  onChange,
  disabled = false,
  size = 20,
  className = '',
}) {
  const formattedValue = formatRating(value)
  const hasRating = formattedValue !== null && Number(value) > 0
  const countLabel = count === null || count === undefined
    ? null
    : `${count} ${Number(count) === 1 ? 'rating' : 'ratings'}`
  const groupLabel = hasRating
    ? `${formattedValue} out of ${stars} stars${countLabel ? `, ${countLabel}` : ''}`
    : 'Not rated yet'

  return (
    <span className={`inline-flex flex-wrap items-center gap-2 text-sm font-black ${className}`}>
      <span className="inline-flex items-center gap-1" role={interactive ? 'group' : undefined} aria-label={groupLabel}>
        {Array.from({ length: stars }).map((_, index) => {
          const starValue = index + 1
          return (
            <RatingStar
              key={starValue}
              fill={clampFill(value, index)}
              size={size}
              label={`Rate ${starValue} out of ${stars} stars`}
              onClick={interactive && onChange ? () => onChange(starValue) : undefined}
              disabled={disabled}
            />
          )
        })}
      </span>
      {showValue ? <span className="text-white">{formattedValue || 'No ratings yet'}</span> : null}
      {showCount && countLabel ? <span className="text-[var(--color-text)]">({countLabel})</span> : null}
    </span>
  )
}

export default Rating

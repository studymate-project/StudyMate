import { Star } from 'lucide-react'

function Rating({ value, count, stars = 5, showValue = true, className = '' }) {
  return (
    <span className={`inline-flex flex-wrap items-center gap-2 text-sm font-black ${className}`}>
      <span className="inline-flex items-center gap-0.5" aria-label={`${value} out of ${stars} stars`}>
        {Array.from({ length: stars }).map((_, index) => (
          <Star key={index} size={15} className="fill-[var(--color-star)] text-[var(--color-star)]" />
        ))}
      </span>
      {showValue ? <span className="text-white">{value}</span> : null}
      {count ? <span className="text-[var(--color-text)]">{count}</span> : null}
    </span>
  )
}

export default Rating

import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

function HorizontalScroller({ children, className = '', ariaLabel = 'Scrollable content' }) {
  const viewportRef = useRef(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)

  const updateScrollState = useCallback(() => {
    const viewport = viewportRef.current
    if (!viewport) return

    const maxScrollLeft = viewport.scrollWidth - viewport.clientWidth
    setCanScrollLeft(viewport.scrollLeft > 1)
    setCanScrollRight(maxScrollLeft - viewport.scrollLeft > 1)
  }, [])

  useEffect(() => {
    const viewport = viewportRef.current
    if (!viewport) return undefined

    updateScrollState()
    viewport.addEventListener('scroll', updateScrollState, { passive: true })
    window.addEventListener('resize', updateScrollState)

    const resizeObserver = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(updateScrollState)
    resizeObserver?.observe(viewport)

    return () => {
      viewport.removeEventListener('scroll', updateScrollState)
      window.removeEventListener('resize', updateScrollState)
      resizeObserver?.disconnect()
    }
  }, [children, updateScrollState])

  const scroll = (direction) => {
    const viewport = viewportRef.current
    if (!viewport) return

    viewport.scrollBy({
      left: direction * Math.max(viewport.clientWidth * 0.8, 240),
      behavior: 'smooth',
    })
  }

  return (
    <div className={`relative min-w-0 ${className}`}>
      {canScrollLeft ? (
        <button
          type="button"
          aria-label={`Scroll ${ariaLabel} left`}
          onClick={() => scroll(-1)}
          className="absolute left-2 top-1/2 z-10 hidden h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)]/95 text-[var(--color-text)] shadow-lg transition-colors hover:border-[var(--color-primary-light)] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] md:flex"
        >
          <ChevronLeft size={20} aria-hidden="true" />
        </button>
      ) : null}
      <div ref={viewportRef} aria-label={ariaLabel} className="horizontal-scroll flex min-w-0 max-w-full snap-x snap-proximity gap-5 overflow-x-auto px-1 pb-4 pt-1">
        {children}
      </div>
      {canScrollRight ? (
        <button
          type="button"
          aria-label={`Scroll ${ariaLabel} right`}
          onClick={() => scroll(1)}
          className="absolute right-2 top-1/2 z-10 hidden h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)]/95 text-[var(--color-text)] shadow-lg transition-colors hover:border-[var(--color-primary-light)] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] md:flex"
        >
          <ChevronRight size={20} aria-hidden="true" />
        </button>
      ) : null}
    </div>
  )
}

export default HorizontalScroller

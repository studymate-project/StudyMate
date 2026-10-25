import { useId, useLayoutEffect, useRef, useState } from 'react'
import { getQuestionDescriptionToggleLabel } from './questionDescriptionState'

function QuestionDescription({ description = '', className = '' }) {
  const contentId = useId()
  const measureRef = useRef(null)
  const [expanded, setExpanded] = useState(false)
  const [hasOverflow, setHasOverflow] = useState(false)

  useLayoutEffect(() => {
    const measure = () => {
      const element = measureRef.current
      if (!element) return
      const lineHeight = Number.parseFloat(window.getComputedStyle(element).lineHeight)
      setHasOverflow(element.scrollHeight > lineHeight + 1)
    }

    measure()
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(measure)
    if (observer && measureRef.current) observer.observe(measureRef.current)
    window.addEventListener('resize', measure)
    return () => {
      observer?.disconnect()
      window.removeEventListener('resize', measure)
    }
  }, [description])

  const label = getQuestionDescriptionToggleLabel(hasOverflow, expanded)

  return <div className={className}>
    <p id={contentId} className={`text-sm font-black leading-relaxed text-[var(--color-text)] ${hasOverflow && !expanded ? 'line-clamp-1' : ''}`}>{description}</p>
    <span ref={measureRef} aria-hidden="true" className="pointer-events-none absolute h-auto w-full whitespace-pre-wrap break-words text-sm font-black leading-relaxed invisible">{description}</span>
    {label ? <button type="button" aria-controls={contentId} aria-expanded={expanded} onClick={(event) => { event.preventDefault(); event.stopPropagation(); setExpanded((value) => !value) }} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') event.stopPropagation() }} className="mt-1 text-sm font-black text-[var(--color-primary-light)] underline decoration-transparent underline-offset-2 hover:decoration-current focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]">{label}</button> : null}
  </div>
}

export default QuestionDescription

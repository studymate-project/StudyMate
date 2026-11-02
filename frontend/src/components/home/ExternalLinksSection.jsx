import { useEffect, useRef, useState } from 'react'
import { getApiErrorMessage } from '../../api'
import { useResourceList } from '../../hooks/useResourceList'
import HorizontalScroller from '../common/HorizontalScroller'
import { ResourceGridSkeleton } from '../common/Skeletons'
import ResourceCard from './ResourceCard'

const LINK_PARAMS = { resource_type: 'link', ordering: 'latest', page_size: 4 }

function ExternalLinksSection() {
  const sectionRef = useRef(null)
  const [isNearViewport, setIsNearViewport] = useState(false)

  useEffect(() => {
    const section = sectionRef.current
    if (!section || typeof IntersectionObserver === 'undefined') {
      setIsNearViewport(true)
      return undefined
    }

    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return
      setIsNearViewport(true)
      observer.disconnect()
    }, { rootMargin: '600px 0px' })

    observer.observe(section)
    return () => observer.disconnect()
  }, [])

  const { resources, loading, error } = useResourceList(isNearViewport ? LINK_PARAMS : null)

  return (
    <section ref={sectionRef} className="page-section pb-12">
      <div className="section-inner">
        <h2 className="section-title">External Links</h2>        
        {isNearViewport && loading ? <ResourceGridSkeleton horizontal /> : null}
        {isNearViewport && !loading && error && !resources.length ? <p className="mt-6 text-sm font-black text-[var(--color-text)]" role="alert">{getApiErrorMessage(error)}</p> : null}
        {isNearViewport && !loading && error && resources.length ? <p className="mt-6 text-sm text-[var(--color-text)]" role="alert">We couldn&apos;t refresh external links. Showing the latest available results.</p> : null}
        {isNearViewport && !loading && !error && !resources.length ? <p className="mt-6 text-sm text-[var(--color-text)]">No external links are available yet.</p> : null}
        {isNearViewport && !loading && resources.length ? (
          <HorizontalScroller className="mt-6" ariaLabel="external links">
            {resources.map((resource) => <div key={resource.id} className="w-[min(82vw,300px)] shrink-0 snap-start sm:w-[280px] lg:w-[290px]"><ResourceCard resource={resource} /></div>)}
          </HorizontalScroller>
        ) : null}
      </div>
    </section>
  )
}

export default ExternalLinksSection

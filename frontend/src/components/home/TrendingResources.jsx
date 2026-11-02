import { getApiErrorMessage } from '../../api'
import { useResourceList } from '../../hooks/useResourceList'
import HorizontalScroller from '../common/HorizontalScroller'
import { ResourceGridSkeleton } from '../common/Skeletons'
import ResourceCard from './ResourceCard'

function TrendingResources() {
  const { resources, loading, error } = useResourceList({ resource_type: 'file', ordering: 'popular', page_size: 4 })

  return (
    <section className="page-section">
      <div className="section-inner">
        <h2 className="section-title">Resources</h2>
        
        {loading ? <ResourceGridSkeleton horizontal /> : null}
          {!loading && error && !resources.length ? <p className="text-sm font-black text-[var(--color-text)]" role="alert">{getApiErrorMessage(error)}</p> : null}
          {!loading && error && resources.length ? <p className="mt-6 text-sm text-[var(--color-text)]" role="alert">We couldn&apos;t refresh resources. Showing the latest available results.</p> : null}
          {!loading && !error && resources.length === 0 ? <p className="text-sm font-black text-[var(--color-text)]">No resources available yet.</p> : null}
          {!loading && resources.length ? (
            <HorizontalScroller className="mt-6" ariaLabel="resources">
              {resources.map((resource) => <div key={resource.id} className="w-[min(82vw,300px)] shrink-0 snap-start sm:w-[280px] lg:w-[290px]"><ResourceCard resource={resource} /></div>)}
            </HorizontalScroller>
          ) : null}
      </div>
    </section>
  )
}

export default TrendingResources

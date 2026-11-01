import { getApiErrorMessage } from '../../api'
import { useResourceList } from '../../hooks/useResourceList'
import { ResourceGridSkeleton } from '../common/Skeletons'
import ResourceCard from './ResourceCard'

function TrendingResources() {
  const { resources, loading, error } = useResourceList({ ordering: 'popular', page_size: 4 })

  return (
    <section className="page-section">
      <div className="section-inner">
        <h2 className="section-title">Resources</h2>
        <p className="section-copy">Most viewed and downloaded this week</p>
        <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {loading ? <ResourceGridSkeleton /> : null}
          {!loading && error && !resources.length ? <p className="text-sm font-black text-[var(--color-text)]" role="alert">{getApiErrorMessage(error)}</p> : null}
          {!loading && error && resources.length ? <p className="col-span-full text-sm text-[var(--color-text)]" role="alert">We couldn&apos;t refresh resources. Showing the latest available results.</p> : null}
          {!loading && !error && resources.length === 0 ? <p className="text-sm font-black text-[var(--color-text)]">No resources available yet.</p> : null}
          {!loading && resources.length
            ? resources.map((resource) => <ResourceCard key={resource.id} resource={resource} />)
            : null}
        </div>
      </div>
    </section>
  )
}

export default TrendingResources

import ResourceListItem from './ResourceListItem'
import { getApiErrorMessage } from '../../api'
import Spinner from '../common/Spinner'

function ResourceList({ resources, loading, error }) {
  return (
    <section className="mt-7">
      <h2 className="text-sm font-black text-white">All Resources</h2>
      <div className="mt-3 space-y-3">
        {loading ? <div className="flex justify-center py-2"><Spinner label="Loading resources" /></div> : null}
        {!loading && error ? <p className="text-sm font-black text-[var(--color-text)]">{getApiErrorMessage(error)}</p> : null}
        {!loading && !error && resources.length === 0 ? <p className="text-sm font-black text-[var(--color-text)]">No resources found.</p> : null}
        {!loading && !error ? resources.map((resource) => <ResourceListItem key={resource.id} resource={resource} />) : null}
      </div>
    </section>
  )
}

export default ResourceList

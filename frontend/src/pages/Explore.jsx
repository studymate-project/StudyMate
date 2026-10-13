import { useResourceList } from '../hooks/useResourceList'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import ResourceList from '../components/explore/ResourceList'
import SubjectGrid from '../components/explore/SubjectGrid'

const sortTabs = ['Most Popular', 'Latest', 'Top Rated', 'Most Downloaded']
const sortOrdering = {
  'Most Popular': 'popular',
  Latest: 'latest',
  'Top Rated': 'top_rated',
  'Most Downloaded': 'most_downloaded',
}

function Explore() {
  const [activeSort, setActiveSort] = useState(sortTabs[0])
  const [searchParams] = useSearchParams()
  const searchParamsKey = searchParams.toString()
  const requestParams = useMemo(() => {
    const currentSearchParams = new URLSearchParams(searchParamsKey)
    const params = {
      page: 1,
      page_size: 20,
      ordering: sortOrdering[activeSort],
    }

    for (const key of ['search', 'subject', 'topic', 'resource_type', 'academic_level', 'difficulty', 'uploader']) {
      const value = currentSearchParams.get(key)
      if (value) params[key] = value
    }

    const tags = currentSearchParams.getAll('tags').filter(Boolean)
    if (tags.length) params.tags = tags

    return params
  }, [activeSort, searchParamsKey])
  const { resources, loading, error } = useResourceList(requestParams)

  return (
    <div className="mx-auto w-full max-w-[1260px]">
      <section className="min-w-0 px-5 py-8 sm:px-8 lg:px-10">
        <h1 className="text-3xl font-black text-white sm:text-4xl">Explore Study Resources</h1>

        <div className="mt-7 flex flex-wrap gap-3" role="tablist" aria-label="Sort resources">
          {sortTabs.map((tab) => {
            const isActive = activeSort === tab
            return (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => setActiveSort(tab)}
                className={[
                  'min-h-12 border-2 px-5 text-base font-black transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]',
                  isActive
                    ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-white'
                    : 'border-[var(--color-border-strong)] bg-transparent text-[var(--color-text)] hover:text-white',
                ].join(' ')}
              >
                {tab}
              </button>
            )
          })}
        </div>

        <SubjectGrid />
        <ResourceList resources={resources} loading={loading} error={error} />
      </section>
    </div>
  )
}

export default Explore

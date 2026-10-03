import { useResourceList } from '../hooks/useResourceList'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import FilterSidebar from '../components/explore/FilterSidebar'
import ResourceList from '../components/explore/ResourceList'
import SubjectGrid from '../components/explore/SubjectGrid'

const sortTabs = ['Most Popular', 'Latest', 'Top Rated', 'Most Downloaded']
const defaultFilters = { subject: 'all', semester: 'all', resourceTypes: [], difficulties: [] }
const sortOrdering = {
  'Most Popular': 'popular',
  Latest: 'latest',
  'Top Rated': 'top_rated',
  'Most Downloaded': 'most_downloaded',
}
const resourceTypeValues = {
  'Cheat Sheets': 'cheat_sheet',
  'Question Papers': 'question_paper',
  Assignments: 'assignment',
}

function Explore() {
  const [activeSort, setActiveSort] = useState(sortTabs[0])
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [filters, setFilters] = useState(defaultFilters)
  const [searchParams] = useSearchParams()
  const subject = searchParams.get('subject')
  const activeSubject = subject || (filters.subject !== 'all' ? filters.subject : null)
  const requestParams = useMemo(() => ({
    page_size: 20,
    ordering: sortOrdering[activeSort],
    ...(activeSubject ? { subject: activeSubject } : {}),
    ...(filters.resourceTypes.length === 1 && resourceTypeValues[filters.resourceTypes[0]]
      ? { resource_type: resourceTypeValues[filters.resourceTypes[0]] }
      : {}),
    ...(filters.difficulties.length === 1 ? { difficulty: filters.difficulties[0].toLowerCase() } : {}),
  }), [activeSort, activeSubject, filters.resourceTypes, filters.difficulties])
  const { resources, loading, error } = useResourceList(requestParams)

  const visibleResources = resources.filter((resource) => (
    (filters.resourceTypes.length === 0 || filters.resourceTypes.some((type) => (
      type.toLowerCase().includes(resource.type.toLowerCase())
      || resource.type.toLowerCase().includes(type.replace('s', '').toLowerCase())
    )))
    && (filters.difficulties.length === 0 || filters.difficulties.includes(resource.difficulty))
  ))

  return (
    <div className="mx-auto grid w-full max-w-[1260px] lg:grid-cols-[260px_minmax(0,1fr)] xl:grid-cols-[260px_minmax(0,1fr)]">
      <div className="lg:block">
        <div className="border-b border-[var(--color-border)] bg-[var(--color-surface-muted)] p-4 lg:hidden">
          <button
            type="button"
            onClick={() => setFiltersOpen((open) => !open)}
            className="h-11 w-full border-2 border-[var(--color-border-strong)] text-base font-black text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
          >
            {filtersOpen ? 'Hide Filters' : 'Show Filters'}
          </button>
        </div>
        <div className={filtersOpen ? 'block' : 'hidden lg:block'}>
          <FilterSidebar onApply={setFilters} />
        </div>
      </div>

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
        <ResourceList resources={visibleResources} loading={loading} error={error} />
      </section>
    </div>
  )
}

export default Explore

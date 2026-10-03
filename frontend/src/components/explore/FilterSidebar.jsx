import { useState } from 'react'
import Button from '../common/Button'
import CheckboxFilter from './CheckboxFilter'
import FilterGroup from './FilterGroup'
import SelectFilter from './SelectFilter'

const resourceTypes = ['PDF Notes', 'Cheat Sheets', 'Videos', 'Question Papers', 'Assignments']
const difficulties = ['Beginner', 'Intermediate', 'Advanced']

const defaultFilters = {
  subject: 'all',
  semester: 'all',
  resourceTypes: [],
  difficulties: [],
}

function FilterSidebar({ onApply }) {
  const [filters, setFilters] = useState(defaultFilters)

  const toggleListValue = (key, label, checked) => {
    setFilters((current) => ({
      ...current,
      [key]: checked ? [...current[key], label] : current[key].filter((item) => item !== label),
    }))
  }

  return (
    <aside className="border-2 border-l-0 border-t-0 border-[var(--color-border)] bg-[var(--color-surface-muted)] p-5 lg:min-h-[calc(100svh-64px)]">
      <h2 className="text-base font-black text-white">Filters</h2>
      <div className="mt-5 h-px bg-[var(--color-border-strong)]" />

      <div className="mt-6 space-y-6">
        <FilterGroup label="Subject">
          <SelectFilter
            label="Subject"
            value={filters.subject}
            onChange={(subject) => setFilters((current) => ({ ...current, subject }))}
            options={[
              { value: 'all', label: 'All Subjects' },
              { value: 'java', label: 'Java' },
              { value: 'dsa', label: 'DSA' },
              { value: 'dbms', label: 'DBMS' },
              { value: 'os', label: 'OS' },
            ]}
          />
        </FilterGroup>

        <FilterGroup label="Semester">
          <SelectFilter
            label="Semester"
            value={filters.semester}
            onChange={(semester) => setFilters((current) => ({ ...current, semester }))}
            options={[
              { value: 'all', label: 'All Semesters' },
              { value: '1', label: 'Semester 1' },
              { value: '2', label: 'Semester 2' },
              { value: '3', label: 'Semester 3' },
              { value: '4', label: 'Semester 4' },
            ]}
          />
        </FilterGroup>

        <FilterGroup label="Resource Type">
          <div className="space-y-2">
            {resourceTypes.map((type) => (
              <CheckboxFilter
                key={type}
                label={type}
                checked={filters.resourceTypes.includes(type)}
                onChange={(checked) => toggleListValue('resourceTypes', type, checked)}
              />
            ))}
          </div>
        </FilterGroup>

        <FilterGroup label="Difficulty">
          <div className="space-y-2">
            {difficulties.map((difficulty) => (
              <CheckboxFilter
                key={difficulty}
                label={difficulty}
                checked={filters.difficulties.includes(difficulty)}
                onChange={(checked) => toggleListValue('difficulties', difficulty, checked)}
              />
            ))}
          </div>
        </FilterGroup>
      </div>

      <div className="mt-7 grid gap-3">
        <Button className="w-full" onClick={() => onApply?.(filters)}>Apply Filters</Button>
        <Button
          variant="secondary"
          className="w-full border-[var(--color-border-strong)] text-[var(--color-text)] hover:text-white"
          onClick={() => {
            setFilters(defaultFilters)
            onApply?.(defaultFilters)
          }}
        >
          Clear All
        </Button>
      </div>
    </aside>
  )
}

export default FilterSidebar

import { useState } from 'react'
import CheckboxFilter from '../explore/CheckboxFilter'

function SearchFilters({ groups }) {
  const [selected, setSelected] = useState([])

  const toggle = (label, checked) => {
    setSelected((current) => (checked ? [...current, label] : current.filter((item) => item !== label)))
  }

  return (
    <aside className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 lg:min-h-[calc(100svh-64px)]">
      <h2 className="text-base font-black text-white">Filters</h2>
      <div className="mt-5 h-px bg-[var(--color-border-strong)]" />
      <div className="mt-6 space-y-6">
        {groups.map((group) => (
          <fieldset key={group.title} className="space-y-2">
            <legend className="mb-2 text-sm font-black text-white">{group.title}</legend>
            {group.options.map((option) => (
              <CheckboxFilter key={option} label={option} checked={selected.includes(option)} onChange={(checked) => toggle(option, checked)} />
            ))}
          </fieldset>
        ))}
      </div>
    </aside>
  )
}

export default SearchFilters

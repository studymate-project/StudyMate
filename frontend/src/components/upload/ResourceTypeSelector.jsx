const resourceTypes = ['File', 'Video', 'Link']

function ResourceTypeSelector({ value, onChange }) {
  return <div className="flex flex-wrap gap-2" role="group" aria-label="Resource type">
    {resourceTypes.map((type) => <button key={type} type="button" onClick={() => onChange(type)} className={`min-h-10 border px-4 text-sm font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)] ${value === type ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-white' : 'border-[var(--color-border-strong)] text-[var(--color-text)] hover:border-[var(--color-primary-light)] hover:text-white'}`}>{type}</button>)}
  </div>
}

export default ResourceTypeSelector

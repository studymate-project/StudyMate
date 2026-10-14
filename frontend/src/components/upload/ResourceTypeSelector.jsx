const resourceTypes = ['File', 'Video', 'Link']

function ResourceTypeSelector({ value, onChange }) {
  return <div className="flex flex-wrap gap-2" role="group" aria-label="Resource type">
    {resourceTypes.map((type) => <button key={type} type="button" onClick={() => onChange(type)} className={`min-h-10 rounded-lg border px-4 text-sm font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] ${value === type ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-primary-dark)]' : 'border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text)] hover:border-[var(--color-focus)] hover:bg-[var(--color-blue-hover)]'}`}>{type}</button>)}
  </div>
}

export default ResourceTypeSelector

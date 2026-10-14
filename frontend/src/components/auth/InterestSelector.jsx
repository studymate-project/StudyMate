const interests = ['Java', 'DSA', 'DBMS', 'Web Development', 'Python', 'AI/ML']

function InterestSelector({ selected, onChange }) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-medium text-[var(--color-text)]">Interests <span className="text-xs font-normal">(optional)</span></legend>
      <div className="flex flex-wrap gap-2">
        {interests.map((interest) => {
          const active = selected.includes(interest)
          return <button key={interest} type="button" aria-pressed={active} onClick={() => onChange(interest)} className={`min-h-7 rounded-lg border px-3 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] ${active ? 'border-[var(--color-primary)] bg-[var(--color-primary)] text-[var(--color-primary-dark)]' : 'border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-text)] hover:border-[var(--color-focus)] hover:text-white'}`}>{interest}</button>
        })}
      </div>
    </fieldset>
  )
}

export default InterestSelector

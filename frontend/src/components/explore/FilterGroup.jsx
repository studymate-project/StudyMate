function FilterGroup({ label, children }) {
  return (
    <fieldset className="space-y-3">
      <legend className="text-xs font-black uppercase tracking-wide text-[var(--color-text)]">{label}</legend>
      {children}
    </fieldset>
  )
}

export default FilterGroup

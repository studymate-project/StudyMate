function SelectFilter({ label, value, onChange, options }) {
  return (
    <label className="block">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-12 w-full border-2 border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-base font-black text-white outline-none focus:border-[var(--color-primary-light)]"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

export default SelectFilter

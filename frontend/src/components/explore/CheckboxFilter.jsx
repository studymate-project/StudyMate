function CheckboxFilter({ label, checked, onChange }) {
  return (
    <label className="flex min-h-8 cursor-pointer items-center gap-3 text-base font-black text-[var(--color-text)]">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-5 w-5 appearance-none border-2 border-[var(--color-border-strong)] bg-transparent checked:border-[var(--color-primary)] checked:bg-[var(--color-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]"
      />
      <span>{label}</span>
    </label>
  )
}

export default CheckboxFilter

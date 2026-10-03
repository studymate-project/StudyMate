function SearchSection({ title, children }) {
  return (
    <section className="mt-7">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-sm font-black uppercase text-[var(--color-text)]">{title}</h2>
        <a href="/" className="text-sm font-black text-[#58a7df] hover:text-white">
          View all -&gt;
        </a>
      </div>
      <div className="mt-3 space-y-3">{children}</div>
    </section>
  )
}

export default SearchSection

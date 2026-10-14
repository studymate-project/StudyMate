import { Link } from 'react-router-dom'

function SearchSection({ title, children, showViewAll = false, viewAllTo }) {
  return (
    <section className="mt-7">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-sm font-black uppercase text-[var(--color-text)]">{title}</h2>
        {showViewAll && viewAllTo && <Link to={viewAllTo} className="text-sm font-black text-[var(--color-text)] hover:text-white">View all -&gt;</Link>}
      </div>
      <div className="mt-3 space-y-3">{children}</div>
    </section>
  )
}

export default SearchSection

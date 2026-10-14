import { Search } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function SearchBar({ placeholder = 'Search anything...' }) {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()

  const handleSubmit = (event) => {
    event.preventDefault()
    const q = query.trim()
    navigate(q ? `/search?q=${encodeURIComponent(q)}` : '/search')
  }

  return (
    <form onSubmit={handleSubmit} className="relative block w-full min-w-0">
      <label>
        <span className="sr-only">Search</span>
        <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-dim)]" size={18} />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={placeholder}
          className="h-12 w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-nav)] py-2 pl-10 pr-3 text-base font-medium text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-dim)] focus:border-[var(--color-focus)]"
        />
      </label>
    </form>
  )
}

export default SearchBar

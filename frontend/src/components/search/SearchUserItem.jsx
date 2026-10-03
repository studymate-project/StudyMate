function SearchUserItem({ user }) {
  return (
    <article className="flex items-center gap-4 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[#073c68] text-sm font-black text-white">{user.initials}</div>
      <div className="min-w-0">
        <h3 className="text-base font-black text-white">{user.name}</h3>
        <p className="text-sm font-black text-[var(--color-text)]">{user.meta}</p>
      </div>
    </article>
  )
}

export default SearchUserItem

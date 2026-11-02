import Avatar from '../common/Avatar'

function SearchUserItem({ user }) {
  return (
    <article className="flex items-center gap-4 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <Avatar user={user} size="lg" decorative />
      <div className="min-w-0">
        <h3 className="text-base font-black text-white">{user.name}</h3>
        <p className="text-sm font-black text-[var(--color-text)]">{user.meta}</p>
      </div>
    </article>
  )
}

export default SearchUserItem

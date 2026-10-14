import { useRef, useState } from 'react'

function ProfileHeader({
  user,
  profile,
  action = null,
  editable = false,
  avatarBusy = false,
  avatarError = '',
  onAvatarFile = null,
  onAvatarUrl = null,
}) {
  return <section className="bg-[var(--color-band)] px-5 py-8 sm:px-8 lg:px-10">
    <div className="mx-auto max-w-[1260px]">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
        <AvatarPicker
          user={user}
          profile={profile}
          editable={editable}
          busy={avatarBusy}
          error={avatarError}
          onFile={onAvatarFile}
          onUrl={onAvatarUrl}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-4"><h1 className="text-2xl font-bold text-white sm:text-3xl">{user.name}</h1>{action ? <div className="sm:ml-auto">{action}</div> : null}</div>
          {(user.course || user.semester) && <p className="mt-2 text-sm text-[var(--color-text)]">{user.course}{user.course && user.semester && <> &middot; </>}{user.semester}</p>}
          {profile.bio && <p className="mt-2 text-sm text-white/90">&ldquo;{profile.bio}&rdquo;</p>}
          {profile.tags.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{profile.tags.map((tag) => <span key={tag} className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-2.5 py-1 text-xs font-medium text-[var(--color-text)]">{tag}</span>)}</div>}
        </div>
      </div>
      {profile.stats.length > 0 && <div className="mt-7 grid grid-cols-2 gap-5 sm:grid-cols-4">{profile.stats.map((stat) => <article key={stat.label} className="text-center"><strong className="block text-xl font-bold text-[var(--color-text)]">{stat.value}</strong><span className="mt-1 block text-xs font-medium text-[var(--color-text)]">{stat.label}</span></article>)}</div>}
    </div>
  </section>
}

function AvatarPicker({ user, profile, editable, busy, error, onFile, onUrl }) {
  const fileInputRef = useRef(null)
  const [open, setOpen] = useState(false)
  const [url, setUrl] = useState('')

  const openPicker = () => {
    setUrl(user.avatarUrl || '')
    setOpen((current) => !current)
  }

  const handleFile = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !onFile) return
    try {
      await onFile(file)
      setOpen(false)
    } catch {
      // The parent keeps the validation or upload error visible in the picker.
    }
  }

  const handleUrl = async () => {
    if (!onUrl) return
    try {
      await onUrl(url.trim())
      setOpen(false)
    } catch {
      // The parent keeps the validation or persistence error visible in the picker.
    }
  }

  const avatar = user.avatarUrl
    ? <img src={user.avatarUrl} alt={`${user.name} avatar`} className="h-16 w-16 rounded-full object-cover" />
    : <span className="flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-surface-muted)] text-xl font-bold text-[var(--color-text)]">{profile.initials}</span>

  if (!editable) return avatar

  return <div className="relative shrink-0">
    <button type="button" onClick={openPicker} disabled={busy} aria-label="Change profile avatar" className="group relative block rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] disabled:opacity-60">
      {avatar}
      <span className="absolute inset-0 flex items-center justify-center rounded-full bg-black/60 text-center text-[10px] font-bold text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">Change<br />avatar</span>
    </button>
    {open ? <div className="absolute left-0 top-[calc(100%+0.75rem)] z-20 w-72 max-w-[calc(100vw-2.5rem)] rounded-lg border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-md">
      <p className="text-sm font-bold text-white">Change profile avatar</p>
      <label className="mt-3 block cursor-pointer rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 py-2 text-center text-sm font-semibold text-[var(--color-text)] hover:bg-[var(--color-blue-hover)]">
        Choose image
        <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={handleFile} className="sr-only" disabled={busy} />
      </label>
      <div className="my-3 flex items-center gap-2 text-xs text-[var(--color-text)]"><span className="h-px flex-1 bg-[var(--color-border)]" />or use a URL<span className="h-px flex-1 bg-[var(--color-border)]" /></div>
      <input type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com/avatar.jpg" className="min-h-10 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-band)] px-2 text-xs text-white outline-none focus:border-[var(--color-focus)]" disabled={busy} />
      <button type="button" onClick={handleUrl} disabled={busy} className="mt-2 min-h-10 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 text-sm font-semibold text-[var(--color-text)] hover:bg-[var(--color-blue-hover)] disabled:cursor-not-allowed disabled:opacity-60">{busy ? 'Saving...' : 'Use this URL'}</button>
      {error ? <p className="mt-3 text-xs text-[var(--color-danger)]" role="alert">{error}</p> : null}
    </div> : null}
  </div>
}

export default ProfileHeader

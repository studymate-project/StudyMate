import { Bell, LogOut, Menu, Search, UserRound, X } from 'lucide-react'
import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { getApiErrorMessage } from '../../api/errors'
import { useAuth } from '../../auth/useAuth'
import IconButton from '../common/IconButton'
import SearchBar from '../common/SearchBar'

const navItems = [
  { label: 'Home', to: '/' },
  { label: 'Explore', to: '/explore' },
  { label: 'Community', to: '/community' },
  { label: 'Upload', to: '/upload' },
]

function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState('')
  const navigate = useNavigate()
  const { status, user, signOut } = useAuth()

  const avatarUrl = user?.profile?.avatar_url || ''
  const displayName = user?.profile?.display_name
    || [user?.first_name, user?.last_name].filter(Boolean).join(' ')
    || user?.username
    || 'Your profile'

  const handleLogout = async () => {
    setIsLoggingOut(true)
    setLogoutError('')
    try {
      await signOut()
      setMenuOpen(false)
      navigate('/login', { replace: true })
    } catch (error) {
      setLogoutError(getApiErrorMessage(error))
    } finally {
      setIsLoggingOut(false)
    }
  }

  const linkClass = ({ isActive }) =>
    [
      'rounded-lg px-2 py-2 text-sm font-medium leading-none transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]',
      isActive ? 'bg-[var(--color-primary-soft)] text-[var(--color-primary-light)]' : 'text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] hover:text-white',
    ].join(' ')

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--color-border)] bg-[var(--color-nav)]">
      <div className="mx-auto flex min-h-16 w-full max-w-[1260px] items-center gap-4 px-4 sm:px-6 lg:px-10">
        <NavLink
          to="/"
          className="mr-2 text-xl font-bold tracking-wide text-[var(--color-primary-light)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--color-focus)]"
          onClick={() => setMenuOpen(false)}
        >
          StudyMate
        </NavLink>

        <nav className="hidden items-center gap-2 md:flex" aria-label="Primary navigation">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={linkClass}>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto hidden min-w-0 max-w-[330px] flex-1 justify-end sm:flex">
          <SearchBar placeholder="Search notes, subjects, topics..." />
        </div>

        <div className="ml-auto flex items-center gap-2 sm:ml-0">
          <IconButton label="Search" className="sm:hidden">
            <Search size={20} />
          </IconButton>
          <Link to="/notifications" aria-label="Notifications" className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-transparent text-[var(--color-text)] transition-colors hover:border-[var(--color-border)] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]"><Bell size={20} /></Link>
          <div className="hidden sm:block">
            <Link to="/profile" aria-label="Your profile" className="inline-flex h-10 w-10 items-center justify-center overflow-hidden rounded-full border border-[var(--color-border)] bg-[var(--color-surface-muted)] text-[var(--color-primary-light)] transition-colors hover:bg-[var(--color-blue-hover)] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]">
              {avatarUrl ? <img src={avatarUrl} alt={`${displayName} avatar`} className="h-full w-full object-cover" /> : <UserRound size={20} />}
            </Link>
          </div>
          {status === 'authenticated' ? <button type="button" onClick={handleLogout} disabled={isLoggingOut} aria-label="Log out" title={logoutError || 'Log out'} className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-transparent text-[var(--color-text)] transition-colors hover:border-[var(--color-border)] hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] disabled:cursor-not-allowed disabled:opacity-60"><LogOut size={19} /></button> : null}
          <IconButton label={menuOpen ? 'Close menu' : 'Open menu'} className="md:hidden" onClick={() => setMenuOpen((open) => !open)}>
            {menuOpen ? <X size={21} /> : <Menu size={21} />}
          </IconButton>
        </div>
      </div>

      {menuOpen ? (
        <div className="border-t border-[var(--color-border)] bg-[var(--color-nav)] px-4 py-4 md:hidden">
          <div className="mx-auto flex max-w-[1260px] flex-col gap-3">
            <SearchBar placeholder="Search anything..." />
            <nav className="grid grid-cols-2 gap-2" aria-label="Mobile navigation">
              {navItems.map((item) => (
                <NavLink key={item.to} to={item.to} className={linkClass} onClick={() => setMenuOpen(false)}>
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <Link
              to="/profile"
              className="min-h-11 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-3 text-left text-sm font-semibold text-[var(--color-primary-light)]"
              onClick={() => setMenuOpen(false)}
            >
              Profile
            </Link>
            {status === 'authenticated' ? <button type="button" onClick={handleLogout} disabled={isLoggingOut} className="min-h-11 border border-[var(--color-border)] px-3 text-left text-sm font-semibold text-[var(--color-text)] disabled:cursor-not-allowed disabled:opacity-60">{isLoggingOut ? 'Logging out…' : 'Log out'}</button> : null}
            {logoutError ? <p role="alert" className="text-xs text-[var(--color-danger)]">{logoutError}</p> : null}
          </div>
        </div>
      ) : null}
    </header>
  )
}

export default Navbar

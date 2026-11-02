import { UserRound } from 'lucide-react'
import { useState } from 'react'

const sizeClasses = {
  xs: 'h-7 w-7',
  sm: 'h-8 w-8',
  md: 'h-10 w-10',
  lg: 'h-12 w-12',
  xl: 'h-20 w-20',
}

function Avatar({ user = {}, size = 'md', className = '', alt, decorative = false }) {
  const source = user?.avatarUrl || user?.avatar_url || ''
  const label = user?.name || user?.username || 'StudyMate member'
  const [failedSource, setFailedSource] = useState('')
  const imageFailed = failedSource === source

  const classes = `${sizeClasses[size] || sizeClasses.md} flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-[var(--color-surface-muted)] text-[var(--color-primary-light)] ${className}`
  const imageAlt = alt || `${label} avatar`

  return (
    <span className={classes} aria-hidden={decorative ? 'true' : undefined}>
      {source && !imageFailed ? <img src={source} alt={decorative ? '' : imageAlt} className="h-full w-full object-cover" onError={() => setFailedSource(source)} /> : <UserRound size={size === 'xl' ? 34 : size === 'lg' ? 24 : size === 'sm' || size === 'xs' ? 16 : 21} aria-hidden="true" />}
    </span>
  )
}

export default Avatar

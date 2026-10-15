import {
  BarChart3,
  BookOpen,
  BrainCircuit,
  Coffee,
  Database,
  Globe2,
  Monitor,
  ScrollText,
  Settings,
} from 'lucide-react'
import { Link } from 'react-router-dom'

const icons = {
  BarChart3,
  BrainCircuit,
  Coffee,
  Database,
  Globe2,
  Monitor,
  ScrollText,
  Settings,
}

function SubjectCard({ subject, compact = false }) {
  const Icon = icons[subject.icon] || BookOpen

  return (
    <Link
      to={`/explore?subject=${subject.slug || subject.name.toLowerCase()}`}
      className={`${subject.colorClass} block min-h-[88px] rounded-xl p-5 text-[var(--color-text)] transition-colors hover:bg-[var(--color-blue-hover)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]`}
    >
      <div className="flex items-start gap-2">
        <Icon size={compact ? 17 : 18} className="mt-0.5 shrink-0 text-[var(--color-teal)]" />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className={`${compact ? 'text-base' : 'text-lg'} font-black leading-tight`}>{subject.name}</h3>
            {subject.isTrending ? <span className="rounded-full bg-[var(--color-primary)] px-2 py-0.5 text-[10px] font-black uppercase tracking-wide text-[var(--color-primary-dark)]">Trending</span> : null}
          </div>
          <p className="mt-3 text-sm font-black text-[var(--color-text-dim)]">{subject.meta || subject.count}</p>
        </div>
      </div>
    </Link>
  )
}

export default SubjectCard

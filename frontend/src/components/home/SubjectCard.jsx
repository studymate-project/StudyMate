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
          <h3 className={`${compact ? 'text-base' : 'text-lg'} font-black leading-tight`}>{subject.name}</h3>
          <p className="mt-3 text-sm font-black text-[var(--color-text-dim)]">{subject.count}</p>
        </div>
      </div>
    </Link>
  )
}

export default SubjectCard

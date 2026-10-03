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
      className={`${subject.colorClass} block min-h-[88px] p-5 text-white transition-transform hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-light)]`}
    >
      <div className="flex items-start gap-2">
        <Icon size={compact ? 17 : 18} className="mt-0.5 shrink-0 text-white/90" />
        <div className="min-w-0">
          <h3 className={`${compact ? 'text-base' : 'text-lg'} font-black leading-tight`}>{subject.name}</h3>
          <p className="mt-3 text-sm font-black text-white/90">{subject.count}</p>
        </div>
      </div>
    </Link>
  )
}

export default SubjectCard

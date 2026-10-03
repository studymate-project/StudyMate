import { BookOpen, Check } from 'lucide-react'

function AuthBrandPanel({ variant }) {
  const isLogin = variant === 'login'
  const title = isLogin ? <>Learn. Share.<br />Discuss. Grow.</> : 'Join the community'
  const copy = isLogin
    ? 'Join thousands of students sharing knowledge and growing together on StudyMate.'
    : 'Learn, share and grow with students like you.'
  const items = isLogin
    ? ['28,000+ study resources', 'Ask questions & get answers', 'Share notes & earn reputation', '12,000+ students community']
    : ['12,840 Students', '28,430 Resources', '8,240 Questions', '100% Free to use']

  return (
    <aside className="flex min-h-[285px] items-center justify-center bg-[#27005c] px-5 py-10 text-center sm:px-10 min-[900px]:min-h-0 min-[900px]:px-12">
      <div className="w-full max-w-[360px]">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-[var(--color-surface)] text-[#48b6ff] sm:h-20 sm:w-20">
          <BookOpen size={35} strokeWidth={1.5} aria-hidden="true" />
        </div>
        <h1 className="mt-7 text-[1.7rem] font-bold leading-[1.28] text-white sm:text-[1.8rem]">{title}</h1>
        <p className="mx-auto mt-7 max-w-[345px] text-sm font-normal leading-5 text-slate-100 sm:text-[0.95rem]">{copy}</p>
        <div className="mx-auto mt-7 max-w-[320px] bg-[var(--color-surface)] px-5 py-3.5 text-left">
          <ul className="space-y-2.5 text-xs font-medium leading-4 text-slate-100">
            {items.map((item) => (
              <li key={item} className="flex items-center gap-2.5">
                {isLogin ? <Check className="shrink-0 text-[var(--color-primary-light)]" size={16} strokeWidth={1.8} aria-hidden="true" /> : null}
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </aside>
  )
}

export default AuthBrandPanel

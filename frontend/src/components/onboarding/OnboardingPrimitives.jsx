import { ArrowLeft, ArrowRight, Check, FileText } from 'lucide-react'

export function OnboardingHeader({ step }) {
  return (
    <header className="onboarding-header">
      <div className="onboarding-brand"><img src="/studymate-logo.svg" alt="" /><span>StudyMate</span></div>
      <p className="onboarding-step-count">Step {step} of 4</p>
      <div className="onboarding-progress" aria-label={`Step ${step} of 4`}>
        {[1, 2, 3, 4].map((item) => <span key={item} className={item <= step ? 'is-complete' : ''} />)}
      </div>
    </header>
  )
}

export function SelectionCard({ selected, onClick, icon, children, type = 'radio' }) {
  return <button type="button" onClick={onClick} className={`selection-card ${selected ? 'is-selected' : ''}`} role={type === 'radio' ? 'radio' : undefined} aria-checked={type === 'radio' ? selected : undefined}>
    <span className={`selection-indicator ${type === 'radio' ? 'is-radio' : ''}`} aria-hidden="true">{selected && type !== 'radio' ? <Check size={14} strokeWidth={3} /> : null}</span>
    {icon ? <span className="selection-icon" aria-hidden="true">{icon}</span> : null}
    <span>{children}</span>
  </button>
}

export function Navigation({ onBack, onNext, nextDisabled, final = false, loading = false }) {
  return <div className={`onboarding-navigation ${!onBack ? 'navigation-single' : ''}`}>
    {onBack ? <button type="button" className="onboarding-button onboarding-button-secondary" onClick={onBack}><ArrowLeft size={18} /> Back</button> : null}
    <button type="button" className="onboarding-button onboarding-button-primary" onClick={onNext} disabled={nextDisabled || loading} aria-busy={loading}>{loading ? 'Saving…' : final ? 'Start Learning' : <>Next <ArrowRight size={18} /></>}</button>
  </div>
}

export function RecommendationCard({ recommendation }) {
  return <article className="recommendation-card">
    <div><span className="recommendation-topic">{recommendation.topic}</span><h3>{recommendation.title}</h3></div>
    <span className="recommendation-type"><FileText size={13} />{recommendation.type}</span>
  </article>
}

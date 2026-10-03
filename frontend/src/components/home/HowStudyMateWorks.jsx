import { howItWorksSteps } from '../../data/howItWorks'
import HowItWorksCard from './HowItWorksCard'

function HowStudyMateWorks() {
  return (
    <section className="page-section pb-12">
      <div className="section-inner">
        <h2 className="section-title">How StudyMate Works</h2>
        <p className="section-copy">Four simple steps to accelerate your learning journey</p>
        <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-4">
          {howItWorksSteps.map((step) => (
            <HowItWorksCard key={step.number} step={step} />
          ))}
        </div>
      </div>
    </section>
  )
}

export default HowStudyMateWorks

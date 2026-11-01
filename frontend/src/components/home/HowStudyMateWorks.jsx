import { howItWorksSteps } from '../../data/howItWorks'
import HowItWorksCard from './HowItWorksCard'

function HowStudyMateWorks() {
  return (
    <section className="page-section pb-12">
      <div className="section-inner">
        <h2 className="section-title">How StudyMate Works</h2>
        <p className="section-copy">Four simple steps to accelerate your learning journey</p>
        <div className="horizontal-scroll mt-6 flex min-w-0 max-w-full snap-x snap-proximity gap-6 overflow-x-auto px-1 pb-4 xl:grid xl:grid-cols-4 xl:overflow-visible xl:pb-0">
          {howItWorksSteps.map((step) => (
            <div key={step.number} className="w-[min(82vw,300px)] shrink-0 snap-start xl:w-auto xl:shrink">
              <HowItWorksCard step={step} />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default HowStudyMateWorks

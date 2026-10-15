import PersonalizedSubjectGrid from '../common/PersonalizedSubjectGrid'

function PopularSubjects() {
  return (
    <section className="page-section">
      <div className="section-inner">
        <h2 className="section-title">Subjects for you</h2>
        <p className="section-copy">Explore subjects matched to your interests and educational background</p>
        <div className="mt-6"><PersonalizedSubjectGrid /></div>
      </div>
    </section>
  )
}

export default PopularSubjects

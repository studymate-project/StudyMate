import { homeSubjects } from '../../data/subjects'
import SubjectCard from './SubjectCard'

function PopularSubjects() {
  return (
    <section className="page-section">
      <div className="section-inner">
        <h2 className="section-title">Popular Subjects</h2>
        <p className="section-copy">Browse top subjects students are studying right now</p>
        <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {homeSubjects.map((subject) => (
            <SubjectCard key={subject.name} subject={subject} />
          ))}
        </div>
      </div>
    </section>
  )
}

export default PopularSubjects

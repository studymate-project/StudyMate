import { exploreSubjects } from '../../data/subjects'
import SubjectCard from '../home/SubjectCard'

function SubjectGrid() {
  return (
    <section className="mt-6">
      <h2 className="text-sm font-black text-white">Subjects</h2>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5 xl:grid-cols-6">
        {exploreSubjects.map((subject) => (
          <SubjectCard key={subject.name} subject={subject} compact />
        ))}
      </div>
    </section>
  )
}

export default SubjectGrid

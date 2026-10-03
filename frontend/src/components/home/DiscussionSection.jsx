import { useEffect, useState } from 'react'
import { listQuestions } from '../../api'
import Button from '../common/Button'
import DiscussionCard from './DiscussionCard'

function DiscussionSection() {
  const [discussions, setDiscussions] = useState([])

  useEffect(() => {
    listQuestions()
      .then(({ questions }) => setDiscussions(questions.slice(0, 3)))
      .catch(() => setDiscussions([]))
  }, [])

  return (
    <section className="bg-[var(--color-band)]">
      <div className="section-inner py-10 sm:py-12">
        <h2 className="section-title">What Students Are Discussing</h2>
        <p className="section-copy">Join the conversation - ask questions, share insights</p>
        <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-3">
          {discussions.map((discussion) => (
            <DiscussionCard key={discussion.id} discussion={discussion} />
          ))}
        </div>
        <Button to="/community" className="mt-8">
          View All Discussions
        </Button>
      </div>
    </section>
  )
}

export default DiscussionSection

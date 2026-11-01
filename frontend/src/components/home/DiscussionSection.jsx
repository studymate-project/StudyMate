import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getApiErrorMessage } from '../../api'
import { fetchQuestionList } from '../../api/questions'
import Button from '../common/Button'
import { DiscussionGridSkeleton } from '../common/Skeletons'
import { QUERY_STALE_TIMES } from '../../query/queryClient'
import { questionKeys } from '../../query/queryKeys'
import DiscussionCard from './DiscussionCard'

function DiscussionSection({ deferUntilVisible = false }) {
  const sectionRef = useRef(null)
  const [isNearViewport, setIsNearViewport] = useState(!deferUntilVisible)

  useEffect(() => {
    if (!deferUntilVisible) return undefined

    const section = sectionRef.current
    if (!section || typeof IntersectionObserver === 'undefined') {
      setIsNearViewport(true)
      return undefined
    }

    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return
      setIsNearViewport(true)
      observer.disconnect()
    }, { rootMargin: '600px 0px' })

    observer.observe(section)
    return () => observer.disconnect()
  }, [deferUntilVisible])

  const shouldLoad = !deferUntilVisible || isNearViewport
  const query = useQuery({
    queryKey: questionKeys.list({}),
    queryFn: () => fetchQuestionList({}),
    enabled: shouldLoad,
    staleTime: QUERY_STALE_TIMES.lists,
  })
  const discussions = query.data?.questions?.slice(0, 3) || []

  return (
    <section ref={sectionRef} className="bg-[var(--color-band)]">
      <div className="section-inner py-10 sm:py-12">
        <h2 className="section-title">What Students Are Discussing</h2>
        <p className="section-copy">Join the conversation - ask questions, share insights</p>
        {query.isPending ? <DiscussionGridSkeleton /> : null}
        {!query.isPending && query.error && !discussions.length ? <p className="mt-6 text-sm font-black text-[var(--color-text)]" role="alert">{getApiErrorMessage(query.error)}</p> : null}
        {!query.isPending && query.error && discussions.length ? <p className="mt-6 text-sm text-[var(--color-text)]" role="alert">We couldn&apos;t refresh discussions. Showing the latest available results.</p> : null}
        {!query.isPending && discussions.length ? <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-3">
          {discussions.map((discussion) => <DiscussionCard key={discussion.id} discussion={discussion} />)}
        </div> : null}
        {!query.isPending && !query.error && !discussions.length ? <p className="mt-6 text-sm text-[var(--color-text)]">No discussions are available yet.</p> : null}
        <Button to="/community" className="mt-8">
          View All Discussions
        </Button>
      </div>
    </section>
  )
}

export default DiscussionSection

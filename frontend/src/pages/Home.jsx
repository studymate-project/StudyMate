import DiscussionSection from '../components/home/DiscussionSection'
import HeroSection from '../components/home/HeroSection'
import HowStudyMateWorks from '../components/home/HowStudyMateWorks'
import PopularSubjects from '../components/home/PopularSubjects'
import TrendingResources from '../components/home/TrendingResources'

function Home() {
  return (
    <>
      <HeroSection />
      <PopularSubjects />
      <TrendingResources />
      <DiscussionSection />
      <HowStudyMateWorks />
    </>
  )
}

export default Home

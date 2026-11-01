import DiscussionSection from '../components/home/DiscussionSection'
import ExternalLinksSection from '../components/home/ExternalLinksSection'
import HeroSection from '../components/home/HeroSection'
import HowStudyMateWorks from '../components/home/HowStudyMateWorks'
import TrendingResources from '../components/home/TrendingResources'
import VideosSection from '../components/home/VideosSection'

function Home() {
  return (
    <>
      <HeroSection />
      <TrendingResources />
      <DiscussionSection deferUntilVisible />
      <VideosSection />
      <ExternalLinksSection />
      <HowStudyMateWorks />
    </>
  )
}

export default Home

import { GraduationCap } from 'lucide-react'
import Button from '../common/Button'

function HeroSection() {
  return (
    <section className="bg-[var(--color-hero)]">
      <div className="mx-auto flex min-h-[370px] max-w-[1260px] flex-col items-center justify-center px-5 py-14 text-center sm:px-6 lg:px-10">
        <h1 className="max-w-4xl text-4xl font-black leading-[0.98] text-white sm:text-6xl lg:text-7xl">
          Learn. Share.
          <span className="block sm:inline"> Discuss.</span>
          <br />
          Grow.
        </h1>
        <p className="mt-3 max-w-4xl text-lg font-black leading-tight text-white/85 sm:text-xl">
          Discover useful study resources, learn from your peers, and build knowledge together.
        </p>
        <div className="mt-8 flex w-full max-w-[500px] flex-col items-stretch justify-center gap-4 sm:flex-row sm:items-center">
          <Button to="/explore" variant="dark" className="sm:min-w-[220px]">
            <GraduationCap size={21} />
            Explore Resources
          </Button>
          <Button to="/community" variant="secondary" className="sm:min-w-[220px]">
            Join the Community
          </Button>
        </div>
        <p className="mt-6 text-sm font-black text-white/80">A collaborative learning platform built for students, by students.</p>
      </div>
    </section>
  )
}

export default HeroSection

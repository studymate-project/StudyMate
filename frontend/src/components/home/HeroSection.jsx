import { FileText, GraduationCap, MessageCircle, PlayCircle } from 'lucide-react'
import Button from '../common/Button'
import './HeroSection.css'

function HeroSection() {
  return (
    <section className="hero-section bg-[var(--color-hero)]">
      <div className="hero-decorations" aria-hidden="true">
        <div className="hero-card hero-card-notes">
          <FileText size={16} />
          <span><strong>Resources</strong><small>Quick revision</small></span>
        </div>
        <div className="hero-card hero-card-video">
          <PlayCircle size={17} />
          <span><strong>Video lessons</strong><small>Learn visually</small></span>
        </div>
        <div className="hero-card hero-card-community">
          <MessageCircle size={16} />
          <span><strong>Community Q&amp;A</strong><small>Learn together</small></span>
        </div>
      </div>
      <div className="hero-content mx-auto flex min-h-[370px] max-w-[1260px] flex-col items-center justify-center px-5 py-14 text-center sm:px-6 lg:px-10">
        <h1 className="hero-heading max-w-4xl text-4xl font-black leading-[0.98] text-white sm:text-6xl lg:text-7xl">
          <span className="hero-word hero-word-learn">Learn.</span>{' '}
          <span className="hero-word hero-word-share">Share.</span>
          <span className="block sm:inline">{' '}<span className="hero-word hero-word-discuss">Discuss.</span></span>
          <br />
          <span className="hero-word hero-word-grow hero-word-accent">Grow.</span>
        </h1>
        <p className="hero-description mt-3 max-w-4xl text-lg font-black leading-tight text-white/85 sm:text-xl">
          Discover useful study resources, learn from your peers, and build knowledge together.
        </p>
        <div className="hero-actions mt-8 flex w-full max-w-[500px] flex-col items-stretch justify-center gap-4 sm:flex-row sm:items-center">
          <Button to="/explore" variant="primary" className="sm:min-w-[220px]">
            <GraduationCap size={21} />
            Explore Resources
          </Button>
          <Button to="/community" variant="secondary" className="sm:min-w-[220px]">
            Join the Community
          </Button>
        </div>
        <p className="hero-caption mt-6 text-sm font-black text-white/80">A collaborative learning platform built for students, by students.</p>
      </div>
    </section>
  )
}

export default HeroSection

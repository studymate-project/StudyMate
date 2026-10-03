import { Link } from 'react-router-dom'

const footerLinks = ['About', 'Terms', 'Privacy', 'Help']

function Footer() {
  return (
    <footer className="border-t border-[var(--color-border)] bg-[#8fa0aa] text-[#263946]">
      <div className="mx-auto flex min-h-16 w-full max-w-[1260px] flex-col justify-between gap-4 px-5 py-5 text-sm font-medium sm:flex-row sm:items-center sm:px-8 lg:px-10">
        <p>StudyMate - Learn. Share. Discuss. Grow.</p>
        <nav className="flex flex-wrap gap-7" aria-label="Footer navigation">
          {footerLinks.map((link) => (
            <Link key={link} to="/" className="hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]">
              {link}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  )
}

export default Footer

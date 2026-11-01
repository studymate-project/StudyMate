import { Link } from 'react-router-dom'

const footerLinks = ['About', 'Terms', 'Privacy', 'Help']

function Footer() {
  return (
    <footer className="border-t border-[var(--color-border)] bg-[var(--color-nav)] text-[var(--color-text)]">
      <div className="site-container flex min-h-16 flex-col justify-between gap-4 py-5 text-sm font-medium sm:flex-row sm:items-center">
        <p>StudyMate - Learn. Share. Discuss. Grow.</p>
        <nav className="flex flex-wrap gap-7" aria-label="Footer navigation">
          {footerLinks.map((link) => (
          <Link key={link} to="/" className="hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]">
              {link}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  )
}

export default Footer

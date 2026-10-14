import { Bookmark } from 'lucide-react'
import Button from './Button'

function EmptyState() {
  return (
    <section className="flex min-h-[250px] flex-col items-center justify-center bg-[var(--color-band)] px-5 py-10 text-center">
      <Bookmark size={42} className="text-[var(--color-text)]" />
      <h2 className="mt-5 text-base font-black text-[var(--color-text)]">No saved resources yet.</h2>
      <p className="mt-5 text-sm font-black text-[var(--color-text)]">Find resources you love and save them for later.</p>
      <Button to="/explore" variant="secondary" className="mt-5">
        Explore Resources
      </Button>
    </section>
  )
}

export default EmptyState

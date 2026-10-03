import { Check } from 'lucide-react'

function UploadGuidelines() {
  const guidelines = ['Only upload original or permitted content', 'Add clear titles and accurate tags', 'Correct subject and topic helps discovery', 'No copyrighted material without permission']
  return <section className="border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4"><h2 className="border-b border-[var(--color-border)] pb-2 text-sm font-semibold text-white">Upload Guidelines</h2><ul className="mt-3 space-y-2 text-xs leading-relaxed text-[var(--color-text)]">{guidelines.map((guideline) => <li key={guideline} className="flex gap-1.5"><Check size={14} className="mt-0.5 shrink-0 text-[#9fe8dd]" />{guideline}</li>)}</ul></section>
}

export default UploadGuidelines

import { FileText } from 'lucide-react'
import Button from '../common/Button'

function PdfPreview({ resourceSlug, resourceUrl, resourceType }) {
  const isLink = resourceType === 'link'
  const isPdf = resourceType === 'pdf'

  return (
    <section className="flex min-h-[245px] flex-col items-center justify-center bg-[var(--color-band)] px-5 py-10 text-center">
      <FileText size={58} className="text-[var(--color-text)]" />
      <p className="mt-4 text-base font-black text-[var(--color-text)]">{isPdf ? 'PDF Preview - Click to expand' : isLink ? 'External Resource' : 'Document Preview - Click to open'}</p>
      <Button className="mt-4" to={`/resources/${resourceSlug}/read`} disabled={!resourceUrl}>{isPdf ? 'Open Full PDF Reader' : isLink ? 'Open Link Reader' : 'Open Document Reader'}</Button>
      {!resourceUrl ? <p className="mt-3 text-sm font-bold text-[#ffadb6]">Media is not available for this resource.</p> : null}
    </section>
  )
}

export default PdfPreview

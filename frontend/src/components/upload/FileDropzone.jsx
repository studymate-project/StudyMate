import { FileText, UploadCloud, X } from 'lucide-react'
import { useRef, useState } from 'react'

const acceptedTypes = ['application/pdf', 'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
const maxSize = 20 * 1024 * 1024

function FileDropzone({ file, onFileChange, error }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const selectFile = (candidate) => {
    if (!candidate) return
    if (!acceptedTypes.includes(candidate.type)) return onFileChange(null, 'Choose a PDF, PPT, PPTX, DOC, or DOCX file.')
    if (candidate.size > maxSize) return onFileChange(null, 'Files must be 20MB or smaller.')
    onFileChange(candidate, '')
  }
  const onDrop = (event) => { event.preventDefault(); setDragging(false); selectFile(event.dataTransfer.files[0]) }
  const size = file ? `${(file.size / 1024 / 1024).toFixed(file.size > 1024 * 1024 ? 1 : 2)} MB` : ''
  return <section>
    <input ref={inputRef} type="file" className="sr-only" accept=".pdf,.ppt,.pptx,.doc,.docx" onChange={(event) => selectFile(event.target.files[0])} />
    {file ? <div className="border border-[#8168e8] bg-[var(--color-primary-dark)] p-5 text-center"><FileText className="mx-auto text-white" size={32} /><p className="mt-3 truncate font-semibold text-white">{file.name}</p><p className="mt-1 text-sm text-[#d7d1ff]">{size}</p><button type="button" onClick={() => { onFileChange(null, ''); if (inputRef.current) inputRef.current.value = '' }} className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-white hover:text-[#d7d1ff]"><X size={16} />Remove file</button></div> : <div role="button" tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click() }} onClick={() => inputRef.current?.click()} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={onDrop} className={`cursor-pointer border p-7 text-center transition-colors ${dragging ? 'border-[#d7d1ff] bg-[#3b1c96]' : 'border-[var(--color-primary-dark)] bg-[var(--color-primary-dark)]'}`}><UploadCloud className="mx-auto text-white" size={39} /><p className="mt-4 font-semibold text-white">Drag and drop file here</p><p className="mt-1 text-sm text-[#d7d1ff]">or</p><span className="mt-3 inline-flex min-h-10 items-center bg-[var(--color-surface-muted)] px-4 text-sm font-semibold text-white">Choose File</span><p className="mt-3 text-xs font-medium text-[#d7d1ff]">PDF, PPT, DOCX · Max 20MB</p></div>}
    {error ? <p className="mt-2 text-sm font-medium text-[#ffadb6]">{error}</p> : null}
  </section>
}

export default FileDropzone

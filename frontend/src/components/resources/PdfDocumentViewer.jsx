import { useEffect, useRef, useState } from 'react'
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist/legacy/build/pdf.mjs'
import workerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url'

GlobalWorkerOptions.workerSrc = workerUrl

function destroyPdfObject(object) {
  try {
    return Promise.resolve(object?.destroy()).catch(() => {})
  } catch {
    return Promise.resolve()
  }
}

function PdfDocumentViewer({ url, onReady, onError }) {
  const viewerRef = useRef(null)
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    let cancelled = false
    let loadingTask
    let documentProxy
    const viewerElement = viewerRef.current

    if (viewerElement) viewerElement.replaceChildren()

    async function renderDocument() {
      try {
        const response = await fetch(url, { credentials: 'omit' })
        if (!response.ok) throw new Error(`PDF request failed with status ${response.status}`)
        const data = await response.arrayBuffer()
        loadingTask = getDocument({
          data,
          disableWorker: true,
        })
        documentProxy = await loadingTask.promise
        if (cancelled) return

        const viewer = viewerElement
        if (!viewer) return

        for (let pageNumber = 1; pageNumber <= documentProxy.numPages; pageNumber += 1) {
          const page = await documentProxy.getPage(pageNumber)
          if (cancelled) return

          const baseViewport = page.getViewport({ scale: 1 })
          const availableWidth = Math.max(viewer.clientWidth - 32, 280)
          const scale = Math.min(availableWidth / baseViewport.width, 1.5)
          const viewport = page.getViewport({ scale })
          const deviceScale = window.devicePixelRatio || 1
          const canvas = document.createElement('canvas')
          const pageWrapper = document.createElement('div')

          canvas.width = Math.ceil(viewport.width * deviceScale)
          canvas.height = Math.ceil(viewport.height * deviceScale)
          canvas.style.width = `${viewport.width}px`
          canvas.style.height = `${viewport.height}px`
          canvas.className = 'block max-w-full bg-white shadow-md'

          pageWrapper.className = 'flex justify-center'
          pageWrapper.appendChild(canvas)
          viewer.appendChild(pageWrapper)

          await page.render({
            canvasContext: canvas.getContext('2d', { alpha: false }),
            viewport,
            transform: deviceScale === 1 ? null : [deviceScale, 0, 0, deviceScale, 0, 0],
          }).promise

          if (pageNumber === 1 && !cancelled) {
            setStatus('ready')
            onReady()
          }
        }
      } catch (error) {
        if (cancelled) return
        setStatus('error')
        onError(error)
      }
    }

    renderDocument()

    return () => {
      cancelled = true
      if (viewerElement) viewerElement.replaceChildren()
      if (loadingTask) destroyPdfObject(loadingTask)
      if (documentProxy) destroyPdfObject(documentProxy)
    }
  }, [onError, onReady, url])

  return (
    <div className="relative min-h-[640px] bg-slate-200 p-4 sm:p-6">
      {status === 'loading' ? <p className="absolute inset-0 z-10 flex items-center justify-center font-bold text-slate-700">Loading document...</p> : null}
      {status === 'error' ? <p className="flex min-h-[590px] items-center justify-center font-bold text-slate-700">Unable to render this PDF.</p> : null}
      <div ref={viewerRef} className="mx-auto flex max-w-[900px] flex-col gap-4" aria-label="PDF document pages" />
    </div>
  )
}

export default PdfDocumentViewer

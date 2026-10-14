import { Bookmark, Filter, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getApiErrorMessage, listSavedResources, unsaveResource } from '../api'
import EmptyState from '../components/common/EmptyState'
import Button from '../components/common/Button'
import Spinner from '../components/common/Spinner'
import Footer from '../components/layout/Footer'
import Toast from '../components/common/Toast'

const savedTabs = ['All', 'PDFs', 'Videos', 'Notes', 'Questions']

function SavedResources() {
  const [activeTab, setActiveTab] = useState(savedTabs[0])
  const [items, setItems] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [removingId, setRemovingId] = useState(null)
  const [toast, setToast] = useState(null)

  useEffect(() => {
    let isActive = true

    listSavedResources().then(
      (data) => {
        if (!isActive) return
        setItems(data.resources.map((resource) => ({ id: resource.id, type: 'resource', target: resource })))
        setStatus('success')
      },
      (requestError) => {
        if (!isActive) return
        setError(requestError)
        setStatus('error')
      },
    )

    return () => { isActive = false }
  }, [reloadKey])

  const hydratedItems = useMemo(() => items.filter((saved) => {
    if (activeTab === 'All') return true
    if (activeTab === 'Questions' || activeTab === 'Videos') return false
    return saved.target.type === activeTab.slice(0, -1) || saved.target.type === activeTab
  }), [activeTab, items])

  const retry = () => {
    setStatus('loading')
    setError(null)
    setReloadKey((key) => key + 1)
  }

  const removeSaved = async (resourceId) => {
    if (removingId !== null) return

    setRemovingId(resourceId)
    try {
      const result = await unsaveResource(resourceId)
      if (result.saved === false) {
        setItems((current) => current.filter((item) => item.target.id !== resourceId))
      }
    } catch (requestError) {
      setToast({ message: getApiErrorMessage(requestError), type: 'error' })
    } finally {
      setRemovingId(null)
    }
  }

  if (status === 'loading') {
    return <SavedResourcesPageState loadingLabel="Loading saved resources" />
  }

  if (status === 'error') {
    const isUnauthenticated = error?.status === 401
    return <SavedResourcesPageState
      title={isUnauthenticated ? 'Sign in required' : 'Unable to load saved resources'}
      message={isUnauthenticated ? 'Sign in to view your saved resources.' : getApiErrorMessage(error)}
      action={isUnauthenticated
        ? <Button to="/login" variant="secondary" className="mt-5">Sign in</Button>
        : <button type="button" onClick={retry} className="mt-5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-5 py-2 text-sm font-semibold text-[var(--color-text)] hover:bg-[var(--color-blue-hover)]">Try again</button>}
    />
  }

  return (
    <>
      <div className="mx-auto w-full max-w-[1260px] px-5 py-12 sm:px-8 lg:px-10">
        <header>
          <h1 className="text-4xl font-black text-white">Saved Resources</h1>
          <p className="mt-4 text-base font-black text-[var(--color-text)]">Your collection of useful learning resources.</p>
        </header>

        <div className="mt-10 grid gap-6 lg:grid-cols-[minmax(0,1fr)_220px] lg:items-end">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5" role="tablist" aria-label="Saved resource types">
            {savedTabs.map((tab) => {
              const active = activeTab === tab
              return <button key={tab} type="button" role="tab" aria-selected={active} onClick={() => setActiveTab(tab)} className={`min-h-12 border-b-4 px-4 text-base font-black transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)] ${active ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)] text-[var(--color-primary-light)]' : 'border-transparent text-[var(--color-text)] hover:text-white'}`}>{tab}</button>
            })}
          </div>
          <button type="button" className="inline-flex min-h-11 items-center justify-center gap-2 border-2 border-[var(--color-border)] px-4 text-sm font-black text-[var(--color-text)]">
            <Filter size={18} />Sort: Recently Saved
          </button>
        </div>

        <p className="mt-8 text-sm font-black text-[var(--color-text)]">{hydratedItems.length} saved resources</p>
        <section className="mt-8 space-y-4">
          {hydratedItems.map((saved) => <SavedItem key={saved.id} saved={saved} isRemoving={removingId === saved.target.id} onRemove={() => removeSaved(saved.target.id)} />)}
        </section>

        {hydratedItems.length === 0 ? <div className="mt-8"><EmptyState /></div> : null}
      </div>
      <Footer />
      {toast ? <Toast {...toast} onDismiss={() => setToast(null)} /> : null}
    </>
  )
}

function SavedItem({ saved, isRemoving, onRemove }) {
  const target = saved.target
  const to = `/resources/${target.slug}`

  return (
    <article className="grid gap-4 border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-5 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
      <Link to={to} className="min-w-0">
        <h3 className="break-words text-lg font-black text-white">{target.title}</h3>
        <div className="mt-2 flex flex-wrap gap-2">
          <span className="rounded-full bg-[var(--color-blue)] px-3 py-1 text-sm font-black text-white">{target.subject}</span>
          <span className="rounded-full border border-[var(--color-primary-light)] px-3 py-1 text-sm font-black text-[var(--color-primary-light)]">{target.type}</span>
        </div>
        <p className="mt-3 text-sm font-black text-[var(--color-text)]">by {target.author?.name || 'StudyMate member'}</p>
        <p className="mt-4 text-sm font-black text-[var(--color-text)]">{target.views == null ? 'View count unavailable' : `${Number(target.views).toLocaleString('en-IN')} Views`}</p>
      </Link>

      <div className="flex flex-col items-stretch gap-6 md:items-end">
        <div className="flex justify-end gap-3">
          <Bookmark size={18} className="fill-current text-[var(--color-text)]" />
          <button type="button" onClick={onRemove} disabled={isRemoving} aria-label={`Remove ${target.title}`} className="text-[var(--color-text)] hover:text-white disabled:cursor-not-allowed disabled:opacity-50"><Trash2 size={19} /></button>
        </div>
        <Button to={to} className="bg-[var(--color-blue)] hover:bg-[var(--color-blue-hover)]">Open Resource</Button>
      </div>
    </article>
  )
}

function SavedResourcesPageState({ title, message, action = null, loadingLabel = '' }) {
  return <><main className="mx-auto flex min-h-[calc(100svh-13rem)] w-full max-w-[1260px] items-center justify-center px-5 py-12 sm:px-8 lg:px-10"><section className="flex w-full max-w-xl items-center justify-center border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-7 text-center">{loadingLabel ? <Spinner label={loadingLabel} /> : <div><h1 className="text-xl font-semibold text-white">{title}</h1><p className="mt-2 text-sm text-[var(--color-text)]">{message}</p>{action}</div>}</section></main><Footer /></>
}

export default SavedResources

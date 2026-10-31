import { useEffect, useMemo, useState } from 'react'
import { getApiErrorMessage, listNotifications, markAllNotificationsRead, markNotificationRead, matchesNotificationTab } from '../api'
import Badge from '../components/common/Badge'
import Button from '../components/common/Button'
import Spinner from '../components/common/Spinner'
import Toast from '../components/common/Toast'
import Footer from '../components/layout/Footer'
import NotificationGroup from '../components/notifications/NotificationGroup'
import NotificationTabs from '../components/notifications/NotificationTabs'

const groups = ['Today', 'Yesterday', 'Earlier']
const notificationTabs = ['All', 'Mentions', 'Answers', 'Upvotes', 'Resources']

function Notifications() {
  const [activeTab, setActiveTab] = useState('All')
  const [notifications, setNotifications] = useState([])
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [pendingReadIds, setPendingReadIds] = useState(new Set())
  const [markingAllRead, setMarkingAllRead] = useState(false)

  useEffect(() => {
    let isActive = true

    listNotifications().then(
      (data) => {
        if (!isActive) return
        setNotifications(data.notifications)
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

  const unreadCount = notifications.filter((notification) => notification.unread).length
  const visible = useMemo(() => notifications.filter((notification) => matchesNotificationTab(notification, activeTab)), [activeTab, notifications])
  const isComingSoon = activeTab === 'Mentions'
  const retry = () => {
    setStatus('loading')
    setError(null)
    setReloadKey((key) => key + 1)
  }

  if (status === 'loading') {
    return <NotificationsPageState loadingLabel="Loading notifications" />
  }

  if (status === 'error') {
    const isUnauthenticated = error?.status === 401
    return <NotificationsPageState
      title={isUnauthenticated ? 'Sign in required' : 'Unable to load notifications'}
      message={isUnauthenticated ? 'Sign in to view your notifications.' : getApiErrorMessage(error)}
      action={isUnauthenticated
        ? <Button to="/login" variant="secondary" className="mt-5">Sign in</Button>
        : <button type="button" onClick={retry} className="mt-5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-muted)] px-5 py-2 text-sm font-semibold text-[var(--color-text)] hover:bg-[var(--color-blue-hover)]">Try again</button>}
    />
  }

  const markRead = async (id) => {
    const notification = notifications.find((item) => item.id === id)
    if (!notification || !notification.unread || pendingReadIds.has(id)) return true

    setPendingReadIds((current) => new Set(current).add(id))
    try {
      const updatedNotification = await markNotificationRead(id)
      setNotifications((current) => current.map((item) => item.id === id ? { ...item, unread: updatedNotification.unread } : item))
      return true
    } catch (requestError) {
      setToast({ message: getApiErrorMessage(requestError), type: 'error' })
      return false
    } finally {
      setPendingReadIds((current) => {
        const next = new Set(current)
        next.delete(id)
        return next
      })
    }
  }

  const markAllRead = async () => {
    if (markingAllRead) return

    setMarkingAllRead(true)
    try {
      await markAllNotificationsRead()
      setNotifications((current) => current.map((notification) => ({ ...notification, unread: false })))
      setToast({ message: 'All notifications marked as read.', type: 'success' })
    } catch (requestError) {
      setToast({ message: getApiErrorMessage(requestError), type: 'error' })
    } finally {
      setMarkingAllRead(false)
    }
  }

  return <><main className="mx-auto min-h-[calc(100svh-8rem)] w-full max-w-[1260px] px-5 py-7 sm:px-8 lg:px-10"><div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><div className="flex flex-wrap items-center gap-3"><h1 className="text-2xl font-bold text-white sm:text-3xl">Notifications</h1>{unreadCount ? <Badge className="min-h-6 text-xs">{unreadCount} New</Badge> : null}</div><p className="mt-2 text-sm font-medium text-[var(--color-text)]">Stay updated with activity on your account.</p></div><Button variant="secondary" className="self-start text-sm" onClick={markAllRead} disabled={markingAllRead}>{markingAllRead ? 'Marking...' : 'Mark all as read'}</Button></div><div className="mt-5"><NotificationTabs tabs={notificationTabs} activeTab={activeTab} onChange={setActiveTab} /></div>{isComingSoon ? <ComingSoonNotificationFeature /> : visible.length ? groups.map((group) => <NotificationGroup key={group} title={group} notifications={visible.filter((notification) => notification.group === group)} onRead={markRead} />) : <section className="mt-7  p-8 text-center"><h2 className="text-lg font-semibold text-white">No Notifications</h2></section>}{!isComingSoon && !unreadCount && visible.length ? <p className="mt-6 text-center text-sm text-[var(--color-text)]">You are all caught up.</p> : null}</main><Footer />{toast ? <Toast {...toast} onDismiss={() => setToast(null)} /> : null}</>
}

function ComingSoonNotificationFeature() {
  return <section className="mt-7  p-8 text-center" aria-labelledby="mentions-coming-soon"><h2 id="mentions-coming-soon" className="text-lg font-semibold text-white">Mentions are coming soon</h2></section>
}

function NotificationsPageState({ title, message, action = null, loadingLabel = '' }) {
  return <><main className="mx-auto flex min-h-[calc(100svh-13rem)] w-full max-w-[1260px] items-center justify-center px-5 py-12 sm:px-8 lg:px-10"><section className="flex w-full max-w-xl items-center justify-center border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-7 text-center">{loadingLabel ? <Spinner label={loadingLabel} /> : <div><h1 className="text-xl font-semibold text-white">{title}</h1><p className="mt-2 text-sm text-[var(--color-text)]">{message}</p>{action}</div>}</section></main><Footer /></>
}

export default Notifications

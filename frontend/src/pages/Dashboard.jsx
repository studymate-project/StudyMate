import ContinueLearningCard from '../components/dashboard/ContinueLearningCard'
import DashboardStats from '../components/dashboard/DashboardStats'
import { RecentNotifications, RecentSaves } from '../components/dashboard/DashboardActivityList'
import RecommendedResources from '../components/dashboard/RecommendedResources'
import WeeklyActivity from '../components/dashboard/WeeklyActivity'
import Footer from '../components/layout/Footer'
import { useEffect, useState } from 'react'
import { listNotifications } from '../api'
import { dashboardData } from '../data/dashboard'
import { getResourcesByIds } from '../data/dataHelpers'

function Dashboard() {
  const [notifications, setNotifications] = useState([])
  const savedResources = getResourcesByIds(dashboardData.recentSaveIds)
  useEffect(() => {
    let active = true
    listNotifications()
      .then(({ notifications: nextNotifications }) => {
        if (active) setNotifications(nextNotifications.slice(0, 3))
      })
      .catch(() => {
        if (active) setNotifications([])
      })
    return () => { active = false }
  }, [])

  return <><main className="mx-auto min-h-[calc(100svh-8rem)] w-full max-w-[1260px] px-5 py-7 sm:px-8 lg:px-10"><header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between"><div><h1 className="text-2xl font-bold text-white sm:text-3xl">{dashboardData.greeting}</h1><p className="mt-1 text-sm font-medium text-[var(--color-text)]">{dashboardData.subtitle}</p></div><p className="text-sm font-medium text-[var(--color-text)]">{dashboardData.date}</p></header><div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.7fr)_minmax(280px,0.86fr)]"><div className="space-y-6"><ContinueLearningCard learning={dashboardData.continueLearning} /><RecommendedResources resources={dashboardData.recommendations} /><WeeklyActivity items={dashboardData.weeklyActivity} /></div><aside className="space-y-6"><DashboardStats stats={dashboardData.stats} /><RecentNotifications notifications={notifications} /><RecentSaves resources={savedResources} /></aside></div></main><Footer /></>
}

export default Dashboard

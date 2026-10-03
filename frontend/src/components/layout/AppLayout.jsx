import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'

function AppLayout() {
  return (
    <div className="min-h-svh bg-[var(--color-bg)] text-[var(--color-text)]">
      <Navbar />
      <main>
        <Outlet />
      </main>
    </div>
  )
}

export default AppLayout

import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { TrialBanner } from '../TrialBanner'
import { Menu } from 'lucide-react'
import { Sidebar, MobileDrawer } from './Sidebar'
import { EyeOfHorus } from '../ui/EyeOfHorus'

export function Layout() {
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <MobileDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />

      <div className="flex-1 md:ml-60 flex flex-col min-w-0">
        {/* Topbar móvil */}
        <header className="md:hidden sticky top-0 z-40 flex items-center gap-3
          bg-obsidian-900 px-4 h-14">
          <button onClick={() => setDrawerOpen(true)}
            className="text-white/80 hover:text-white">
            <Menu className="h-6 w-6" />
          </button>
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 p-1 rounded-md bg-gradient-to-br
              from-gold-400 to-gold-600 flex items-center justify-center">
              <EyeOfHorus className="text-obsidian-900 w-full h-full" strokeWidth={6} />
            </div>
            <span className="text-white font-black tracking-tight">
              SAJJAD<span className="text-gold-500">.</span>
            </span>
          </div>
        </header>

        <main className="flex-1 p-6 lg:p-8 max-w-6xl w-full">
          <TrialBanner />
          <Outlet />
        </main>
      </div>
    </div>
  )
}

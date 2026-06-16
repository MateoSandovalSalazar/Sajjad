import { NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Globe, User, LogOut, X } from 'lucide-react'
import { useAuthStore } from '../../store/auth'
import { EyeOfHorus } from '../ui/EyeOfHorus'

const NAV = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/domains',   icon: Globe,           label: 'Mis dominios' },
  { to: '/account',   icon: User,            label: 'Mi cuenta' },
]

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { clearAuth, user } = useAuthStore()
  const navigate = useNavigate()

  const logout = () => { clearAuth(); navigate('/login'); onNavigate?.() }

  return (
    <>
      {/* Logo */}
      <div className="px-6 py-6 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 p-1.5 rounded-lg bg-gradient-to-br
            from-gold-400 to-gold-600 flex items-center justify-center shadow-gold">
            <EyeOfHorus className="text-obsidian-900 w-full h-full" strokeWidth={6} />
          </div>
          <span className="text-white font-black text-xl tracking-tight">
            SAJJAD<span className="text-gold-500">.</span>
          </span>
        </div>
        <p className="text-white/40 text-xs mt-1 tracking-widest uppercase">
          Attack Surface Monitor
        </p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} end={to === '/dashboard'}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm
              font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-white/15 text-white'
                  : 'text-white/60 hover:text-white hover:bg-white/8'
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="px-3 py-4 border-t border-white/10">
        <div className="px-4 py-2 mb-2">
          <p className="text-white text-sm font-medium truncate">
            {user?.full_name ?? user?.email ?? '—'}
          </p>
          <p className="text-white/40 text-xs truncate">{user?.email}</p>
        </div>
        <button onClick={logout}
          className="flex items-center gap-3 w-full px-4 py-2.5 rounded-xl
            text-sm font-medium text-white/60 hover:text-white
            hover:bg-white/8 transition-all">
          <LogOut className="h-4 w-4" />
          Cerrar sesión
        </button>
      </div>
    </>
  )
}

/** Sidebar fija — solo desktop (≥ md). */
export function Sidebar() {
  return (
    <aside className="hidden md:flex flex-col w-60 bg-obsidian-900 min-h-screen
      fixed left-0 top-0 z-30">
      <SidebarContent />
    </aside>
  )
}

/** Drawer deslizante — solo móvil (< md). */
export function MobileDrawer(
  { open, onClose }: { open: boolean; onClose: () => void },
) {
  return (
    <div className={`md:hidden fixed inset-0 z-50 ${open ? '' : 'pointer-events-none'}`}>
      {/* Backdrop */}
      <div
        onClick={onClose}
        className={`absolute inset-0 bg-black/50 transition-opacity duration-200
          ${open ? 'opacity-100' : 'opacity-0'}`}
      />
      {/* Panel */}
      <aside className={`absolute left-0 top-0 h-full w-64 bg-obsidian-900
        flex flex-col shadow-2xl transition-transform duration-200
        ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <button onClick={onClose}
          className="absolute right-3 top-5 text-white/60 hover:text-white z-10">
          <X className="h-5 w-5" />
        </button>
        <SidebarContent onNavigate={onClose} />
      </aside>
    </div>
  )
}

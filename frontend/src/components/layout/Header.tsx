'use client'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'
import { Bell, LogOut, User, ChevronDown } from 'lucide-react'
import { useState } from 'react'

const pageTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/jobs': 'Job Search',
  '/saved': 'Saved Jobs',
  '/applications': 'Applications',
  '/profile': 'Profile',
}

export default function Header() {
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const router = useRouter()
  const [menuOpen, setMenuOpen] = useState(false)

  const title = pageTitles[pathname] || 'JobIntel'

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
      <h1 className="text-xl font-semibold text-slate-900">{title}</h1>

      <div className="flex items-center gap-3">
        <button className="p-2 hover:bg-slate-100 rounded-lg transition-colors relative">
          <Bell className="w-5 h-5 text-slate-500" />
        </button>

        <div className="relative">
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex items-center gap-2 hover:bg-slate-100 rounded-lg px-3 py-2 transition-colors"
          >
            <div className="w-7 h-7 bg-blue-600 rounded-full flex items-center justify-center">
              <User className="w-4 h-4 text-white" />
            </div>
            <span className="text-sm font-medium text-slate-700">{user?.full_name?.split(' ')[0]}</span>
            <ChevronDown className="w-4 h-4 text-slate-400" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-50">
              <div className="px-3 py-2 border-b border-slate-100">
                <p className="text-sm font-medium text-slate-900">{user?.full_name}</p>
                <p className="text-xs text-slate-500">{user?.email}</p>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, Search, Bookmark, Briefcase, User, Target } from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/jobs', label: 'Job Search', icon: Search },
  { href: '/saved', label: 'Saved Jobs', icon: Bookmark },
  { href: '/applications', label: 'Applications', icon: Briefcase },
  { href: '/profile', label: 'Profile', icon: User },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-60 bg-white border-r border-slate-200 flex flex-col">
      <div className="flex items-center gap-2 px-5 py-5 border-b border-slate-200">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <Target className="w-5 h-5 text-white" />
        </div>
        <span className="text-lg font-bold text-slate-900">JobIntel</span>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                active
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              )}
            >
              <Icon className={cn('w-4 h-4', active ? 'text-blue-600' : 'text-slate-400')} />
              {label}
            </Link>
          )
        })}
      </nav>

      <div className="p-3 border-t border-slate-200">
        <div className="bg-blue-50 rounded-lg p-3">
          <p className="text-xs font-medium text-blue-700 mb-1">Pro tip</p>
          <p className="text-xs text-blue-600">Upload your resume to get AI-powered job scores tailored to your profile.</p>
        </div>
      </div>
    </aside>
  )
}

'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import Sidebar from '@/components/layout/Sidebar'
import Header from '@/components/layout/Header'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loadUser } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!user) {
      loadUser().then(() => {
        const { user: u } = useAuth.getState()
        if (!u) router.push('/login')
      })
    }
  }, [])

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}

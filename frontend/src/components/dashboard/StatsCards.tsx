import { TrendingUp, Building2, Send, Calendar, Briefcase } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  newJobsToday: number
  directApplyJobs: number
  applicationsSent: number
  interviewsScheduled: number
  loading?: boolean
}

const Skeleton = () => <div className="h-8 w-16 bg-slate-200 rounded animate-pulse" />

export default function StatsCards({ newJobsToday, directApplyJobs, applicationsSent, interviewsScheduled, loading }: Props) {
  const cards = [
    {
      label: 'New Jobs Today',
      value: newJobsToday,
      icon: TrendingUp,
      color: 'text-green-600',
      bg: 'bg-green-50',
      iconBg: 'bg-green-100',
    },
    {
      label: 'Direct Apply Jobs',
      value: directApplyJobs,
      icon: Building2,
      color: 'text-purple-600',
      bg: 'bg-purple-50',
      iconBg: 'bg-purple-100',
    },
    {
      label: 'Applications Sent',
      value: applicationsSent,
      icon: Send,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
      iconBg: 'bg-blue-100',
    },
    {
      label: 'Interviews Scheduled',
      value: interviewsScheduled,
      icon: Calendar,
      color: 'text-orange-600',
      bg: 'bg-orange-50',
      iconBg: 'bg-orange-100',
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map(({ label, value, icon: Icon, color, bg, iconBg }) => (
        <div key={label} className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-slate-500 font-medium">{label}</p>
            <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center', iconBg)}>
              <Icon className={cn('w-4 h-4', color)} />
            </div>
          </div>
          {loading ? <Skeleton /> : (
            <p className={cn('text-3xl font-bold', color)}>{value.toLocaleString()}</p>
          )}
        </div>
      ))}
    </div>
  )
}

'use client'
import { useEffect, useState } from 'react'
import StatsCards from '@/components/dashboard/StatsCards'
import JobCharts from '@/components/dashboard/JobCharts'
import { applicationsApi, jobsApi } from '@/lib/api'
import type { ApplicationStats } from '@/types'

export default function DashboardPage() {
  const [appStats, setAppStats] = useState<ApplicationStats | null>(null)
  const [jobStats, setJobStats] = useState<{ new_jobs_today: number; direct_apply_jobs: number } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([applicationsApi.stats(), jobsApi.stats()])
      .then(([a, j]) => { setAppStats(a); setJobStats(j) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-1">Overview</h2>
        <p className="text-sm text-slate-500">Your job search at a glance</p>
      </div>

      <StatsCards
        newJobsToday={jobStats?.new_jobs_today ?? 0}
        directApplyJobs={jobStats?.direct_apply_jobs ?? 0}
        applicationsSent={appStats?.applied ?? 0}
        interviewsScheduled={appStats?.interview_scheduled ?? 0}
        loading={loading}
      />

      <div className="mt-8">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Insights</h2>
        <JobCharts />
      </div>
    </div>
  )
}

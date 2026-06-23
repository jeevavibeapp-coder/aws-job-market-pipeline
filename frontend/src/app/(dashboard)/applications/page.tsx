'use client'
import { useEffect, useState } from 'react'
import { applicationsApi } from '@/lib/api'
import type { Application, ApplicationStatus } from '@/types'
import { Briefcase, Loader2, ExternalLink } from 'lucide-react'
import { formatRelativeTime } from '@/lib/utils'

const COLUMNS: { status: ApplicationStatus; label: string; color: string }[] = [
  { status: 'saved', label: 'Saved', color: 'bg-slate-100 border-slate-300' },
  { status: 'applied', label: 'Applied', color: 'bg-blue-50 border-blue-300' },
  { status: 'interview_scheduled', label: 'Interview', color: 'bg-purple-50 border-purple-300' },
  { status: 'offer_received', label: 'Offer', color: 'bg-green-50 border-green-300' },
  { status: 'rejected', label: 'Rejected', color: 'bg-red-50 border-red-300' },
]

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    applicationsApi.list()
      .then(setApplications)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const updateStatus = async (id: string, status: ApplicationStatus) => {
    try {
      const updated = await applicationsApi.update(id, { status })
      setApplications((prev) => prev.map((a) => a.id === id ? updated : a))
    } catch (e) {
      console.error(e)
    }
  }

  const getByStatus = (status: ApplicationStatus) =>
    applications.filter((a) => a.status === status)

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Briefcase className="w-5 h-5 text-blue-600" />
        <h2 className="text-lg font-semibold text-slate-900">Application Tracker</h2>
        <span className="text-sm text-slate-500">({applications.length} total)</span>
      </div>

      {applications.length === 0 ? (
        <div className="text-center py-20 text-slate-400">
          <Briefcase className="w-12 h-12 mx-auto mb-3 opacity-40" />
          <p className="text-lg">No applications tracked yet</p>
          <p className="text-sm mt-1">Click &quot;Track Application&quot; on any job card to add it here</p>
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {COLUMNS.map(({ status, label, color }) => {
            const cols = getByStatus(status)
            return (
              <div key={status} className="min-w-[240px] max-w-[280px]">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-slate-700 text-sm">{label}</h3>
                  <span className="bg-slate-100 text-slate-600 text-xs font-medium px-2 py-0.5 rounded-full">{cols.length}</span>
                </div>
                <div className="space-y-2">
                  {cols.map((app) => (
                    <div key={app.id} className={`rounded-xl border p-4 ${color}`}>
                      <h4 className="font-medium text-slate-900 text-sm line-clamp-2">{app.job.title}</h4>
                      <p className="text-xs text-slate-600 mt-1">{app.job.company.name}</p>
                      {app.applied_at && (
                        <p className="text-xs text-slate-400 mt-1">Applied {formatRelativeTime(app.applied_at)}</p>
                      )}
                      {!app.applied_at && (
                        <p className="text-xs text-slate-400 mt-1">Added {formatRelativeTime(app.created_at)}</p>
                      )}
                      <div className="flex gap-1.5 mt-3 flex-wrap">
                        {COLUMNS.filter((c) => c.status !== status).slice(0, 2).map((c) => (
                          <button
                            key={c.status}
                            onClick={() => updateStatus(app.id, c.status)}
                            className="text-xs border border-slate-300 hover:border-slate-400 text-slate-600 px-2 py-1 rounded-lg transition-colors"
                          >
                            → {c.label}
                          </button>
                        ))}
                        <a
                          href={app.job.direct_apply_url || app.job.job_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-blue-600 border border-blue-200 px-2 py-1 rounded-lg hover:bg-blue-50"
                        >
                          Apply <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    </div>
                  ))}
                  {cols.length === 0 && (
                    <div className="rounded-xl border border-dashed border-slate-200 p-4 text-center text-xs text-slate-400">
                      No {label.toLowerCase()} jobs
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

'use client'
import { useEffect, useState } from 'react'
import { bookmarksApi } from '@/lib/api'
import JobCard from '@/components/jobs/JobCard'
import type { Job } from '@/types'
import { Bookmark, Loader2 } from 'lucide-react'

export default function SavedJobsPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    bookmarksApi.list()
      .then(setJobs)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleBookmarkChange = (jobId: string, saved: boolean) => {
    if (!saved) setJobs((prev) => prev.filter((j) => j.id !== jobId))
  }

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
        <Bookmark className="w-5 h-5 text-blue-600" />
        <h2 className="text-lg font-semibold text-slate-900">Saved Jobs</h2>
        <span className="text-sm text-slate-500">({jobs.length})</span>
      </div>

      {jobs.length === 0 ? (
        <div className="text-center py-20 text-slate-400">
          <Bookmark className="w-12 h-12 mx-auto mb-3 opacity-40" />
          <p className="text-lg">No saved jobs yet</p>
          <p className="text-sm mt-1">Click the bookmark icon on any job to save it here</p>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} onBookmarkChange={handleBookmarkChange} />
          ))}
        </div>
      )}
    </div>
  )
}

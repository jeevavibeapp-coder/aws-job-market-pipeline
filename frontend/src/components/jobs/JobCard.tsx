'use client'
import { useState } from 'react'
import Link from 'next/link'
import { MapPin, Clock, Bookmark, BookmarkCheck, ExternalLink, AlertTriangle, CheckCircle2, Building2 } from 'lucide-react'
import { cn, formatRelativeTime, formatSalary, scoreColor, scoreBg, competitionLabel, sourceLabel } from '@/lib/utils'
import type { Job } from '@/types'
import { bookmarksApi, applicationsApi } from '@/lib/api'

interface Props {
  job: Job
  onBookmarkChange?: (jobId: string, saved: boolean) => void
}

export default function JobCard({ job, onBookmarkChange }: Props) {
  const [saved, setSaved] = useState(false)
  const [applying, setApplying] = useState(false)

  const src = sourceLabel(job.source)
  const comp = competitionLabel(job.competition_score)
  const score = job.score?.overall_score
  const expStatus = job.score?.experience_status

  const applyUrl = job.direct_apply_url || job.company_apply_url || job.job_url

  const toggleSave = async () => {
    try {
      if (saved) {
        await bookmarksApi.remove(job.id)
        setSaved(false)
        onBookmarkChange?.(job.id, false)
      } else {
        await bookmarksApi.save(job.id)
        setSaved(true)
        onBookmarkChange?.(job.id, true)
      }
    } catch (e) {
      console.error(e)
    }
  }

  const handleTrack = async () => {
    setApplying(true)
    try {
      await applicationsApi.create(job.id, 'applied')
    } catch (e) {
      console.error(e)
    } finally {
      setApplying(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', src.color)}>{src.label}</span>
            {expStatus === 'warning' && (
              <span className="inline-flex items-center gap-1 text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full">
                <AlertTriangle className="w-3 h-3" /> Slightly senior
              </span>
            )}
            {expStatus === 'accept' && (
              <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 px-2 py-0.5 rounded-full">
                <CheckCircle2 className="w-3 h-3" /> Good match
              </span>
            )}
          </div>

          <h3 className="font-semibold text-slate-900 text-base truncate">{job.title}</h3>

          <div className="flex items-center gap-1.5 mt-1">
            <Building2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="text-sm text-slate-600">{job.company.name}</span>
          </div>

          <div className="flex items-center gap-4 mt-2 flex-wrap">
            {job.location && (
              <span className="flex items-center gap-1 text-xs text-slate-500">
                <MapPin className="w-3 h-3" /> {job.location}
              </span>
            )}
            <span className="text-xs text-slate-500 capitalize bg-slate-100 px-2 py-0.5 rounded">{job.remote_type}</span>
            {job.posted_at && (
              <span className="flex items-center gap-1 text-xs text-slate-500">
                <Clock className="w-3 h-3" /> {formatRelativeTime(job.posted_at)}
              </span>
            )}
            {job.experience_min !== undefined && (
              <span className="text-xs text-slate-500">{job.experience_min}+ yrs exp</span>
            )}
          </div>

          {job.skills_required.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {job.skills_required.slice(0, 6).map((s) => (
                <span key={s} className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded">{s}</span>
              ))}
              {job.skills_required.length > 6 && (
                <span className="text-xs text-slate-400">+{job.skills_required.length - 6}</span>
              )}
            </div>
          )}

          {job.score?.insight && (
            <p className="mt-3 text-xs text-slate-500 italic line-clamp-2">{job.score.insight}</p>
          )}

          <div className="flex items-center gap-3 mt-3">
            {job.salary_min && (
              <span className="text-xs font-medium text-green-700">
                {formatSalary(job.salary_min, job.salary_max, job.currency)}
              </span>
            )}
            <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', comp.color)}>
              Competition: {comp.label}
            </span>
          </div>
        </div>

        <div className="flex flex-col items-end gap-3 shrink-0">
          {score !== undefined && (
            <div className="text-center">
              <span className={cn('text-3xl font-bold', scoreColor(score))}>{Math.round(score)}</span>
              <p className="text-xs text-slate-400">match</p>
            </div>
          )}

          <button
            onClick={toggleSave}
            className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            title={saved ? 'Remove bookmark' : 'Save job'}
          >
            {saved
              ? <BookmarkCheck className="w-5 h-5 text-blue-600" />
              : <Bookmark className="w-5 h-5 text-slate-400" />}
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-100">
        <a
          href={applyUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 rounded-lg transition-colors text-center flex items-center justify-center gap-2"
        >
          Apply Now
          {(job.direct_apply_url || job.company_apply_url) && <ExternalLink className="w-3.5 h-3.5" />}
        </a>
        <button
          onClick={handleTrack}
          disabled={applying}
          className="flex-1 border border-slate-300 hover:border-slate-400 text-slate-600 text-sm font-medium py-2 rounded-lg transition-colors"
        >
          {applying ? 'Tracking...' : 'Track Application'}
        </button>
      </div>
    </div>
  )
}

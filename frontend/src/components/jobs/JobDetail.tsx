'use client'
import { X, ExternalLink, MapPin, Clock, Building2 } from 'lucide-react'
import type { Job } from '@/types'
import { cn, formatRelativeTime, formatSalary, scoreColor, sourceLabel } from '@/lib/utils'

interface Props {
  job: Job
  onClose: () => void
}

const ScoreBar = ({ label, value }: { label: string; value: number }) => (
  <div>
    <div className="flex items-center justify-between text-xs mb-1">
      <span className="text-slate-600">{label}</span>
      <span className={cn('font-semibold', scoreColor(value))}>{Math.round(value)}</span>
    </div>
    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
      <div
        className={cn('h-full rounded-full', value >= 85 ? 'bg-green-500' : value >= 70 ? 'bg-yellow-500' : 'bg-red-400')}
        style={{ width: `${Math.min(100, value)}%` }}
      />
    </div>
  </div>
)

export default function JobDetail({ job, onClose }: Props) {
  const src = sourceLabel(job.source)
  const applyUrl = job.direct_apply_url || job.company_apply_url || job.job_url
  const score = job.score

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />

      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-slate-200 px-6 py-4 flex items-start justify-between gap-4">
          <div>
            <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', src.color)}>{src.label}</span>
            <h2 className="text-xl font-bold text-slate-900 mt-2">{job.title}</h2>
            <div className="flex items-center gap-1.5 mt-1">
              <Building2 className="w-4 h-4 text-slate-400" />
              <span className="text-slate-600">{job.company.name}</span>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-lg">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-6">
          <div className="flex items-center gap-4 flex-wrap text-sm text-slate-500">
            {job.location && <span className="flex items-center gap-1"><MapPin className="w-4 h-4" /> {job.location}</span>}
            <span className="capitalize bg-slate-100 px-2 py-0.5 rounded">{job.remote_type}</span>
            {job.posted_at && <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> {formatRelativeTime(job.posted_at)}</span>}
            {job.experience_min !== undefined && <span>{job.experience_min}+ yrs experience</span>}
            {job.salary_min && <span className="text-green-700 font-medium">{formatSalary(job.salary_min, job.salary_max, job.currency)}</span>}
          </div>

          {score && (
            <div className="bg-slate-50 rounded-xl p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-900">Match Breakdown</h3>
                <span className={cn('text-3xl font-bold', scoreColor(score.overall_score))}>
                  {Math.round(score.overall_score)}
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <ScoreBar label="Skill Match" value={score.skill_match} />
                <ScoreBar label="Experience Match" value={score.experience_match} />
                <ScoreBar label="Technology Match" value={score.technology_match} />
                <ScoreBar label="Location Match" value={score.location_match} />
                <ScoreBar label="Seniority Match" value={score.seniority_match} />
              </div>
            </div>
          )}

          {score?.insight && (
            <div>
              <h3 className="font-semibold text-slate-900 mb-2">Why this job matches you</h3>
              <p className="text-sm text-slate-600 leading-relaxed bg-blue-50 border border-blue-100 rounded-lg p-4">
                {score.insight}
              </p>
            </div>
          )}

          {job.skills_required.length > 0 && (
            <div>
              <h3 className="font-semibold text-slate-900 mb-2">Required Skills</h3>
              <div className="flex flex-wrap gap-1.5">
                {job.skills_required.map((s) => (
                  <span key={s} className="text-xs bg-slate-100 text-slate-700 px-2.5 py-1 rounded-full">{s}</span>
                ))}
              </div>
            </div>
          )}

          {job.description && (
            <div>
              <h3 className="font-semibold text-slate-900 mb-2">Description</h3>
              <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line line-clamp-[12]">
                {job.description}
              </p>
            </div>
          )}
        </div>

        <div className="sticky bottom-0 bg-white border-t border-slate-200 px-6 py-4">
          <a
            href={applyUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            Apply on {job.direct_apply_url || job.company_apply_url ? 'company site' : 'source'}
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>
    </div>
  )
}

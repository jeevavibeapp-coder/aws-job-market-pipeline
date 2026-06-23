'use client'
import { useState } from 'react'
import JobSearch from '@/components/jobs/JobSearch'
import JobFilters from '@/components/jobs/JobFilters'
import JobCard from '@/components/jobs/JobCard'
import type { Job, SearchRequest } from '@/types'
import { searchApi } from '@/lib/api'
import { Loader2, SlidersHorizontal } from 'lucide-react'

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [processingMs, setProcessingMs] = useState(0)
  const [filtersOpen, setFiltersOpen] = useState(true)

  const handleSearch = async (req: SearchRequest) => {
    setLoading(true)
    setSearched(true)
    try {
      const result = await searchApi.search(req)
      setJobs(result.results as Job[])
      setProcessingMs(result.processing_time_ms)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleNaturalSearch = async (query: string) => {
    setLoading(true)
    setSearched(true)
    try {
      const result = await searchApi.natural(query)
      setJobs(result.results as Job[])
      setProcessingMs(result.processing_time_ms)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <JobSearch onSearch={handleSearch} onNaturalSearch={handleNaturalSearch} />

      <div className="flex gap-6">
        {filtersOpen && (
          <div className="w-64 shrink-0">
            <JobFilters onSearch={handleSearch} />
          </div>
        )}

        <div className="flex-1">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setFiltersOpen(!filtersOpen)}
                className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900 border border-slate-200 rounded-lg px-3 py-1.5 transition-colors"
              >
                <SlidersHorizontal className="w-4 h-4" />
                {filtersOpen ? 'Hide' : 'Show'} filters
              </button>
              {searched && (
                <p className="text-sm text-slate-500">
                  {loading ? 'Searching...' : `${jobs.length} jobs found in ${processingMs}ms`}
                </p>
              )}
            </div>
          </div>

          {loading && (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
          )}

          {!loading && searched && jobs.length === 0 && (
            <div className="text-center py-20 text-slate-500">
              <p className="text-lg font-medium">No jobs matched your criteria</p>
              <p className="text-sm mt-1">Try adjusting filters or lowering the minimum score</p>
            </div>
          )}

          {!loading && !searched && (
            <div className="text-center py-20 text-slate-400">
              <p className="text-lg">Enter your search criteria above to find matching jobs</p>
            </div>
          )}

          <div className="space-y-3">
            {!loading && jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

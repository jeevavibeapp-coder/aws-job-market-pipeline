'use client'
import { useState } from 'react'
import { Search, Sparkles } from 'lucide-react'
import type { SearchRequest } from '@/types'

interface Props {
  onSearch: (req: SearchRequest) => void
  onNaturalSearch: (query: string) => void
}

export default function JobSearch({ onSearch, onNaturalSearch }: Props) {
  const [mode, setMode] = useState<'natural' | 'structured'>('natural')
  const [query, setQuery] = useState('')

  const handleNaturalSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) onNaturalSearch(query.trim())
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={() => setMode('natural')}
          className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg font-medium transition-colors ${
            mode === 'natural' ? 'bg-blue-100 text-blue-700' : 'text-slate-500 hover:bg-slate-100'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          AI Search
        </button>
        <button
          onClick={() => setMode('structured')}
          className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg font-medium transition-colors ${
            mode === 'structured' ? 'bg-blue-100 text-blue-700' : 'text-slate-500 hover:bg-slate-100'
          }`}
        >
          <Search className="w-3.5 h-3.5" />
          Filter Search
        </button>
      </div>

      {mode === 'natural' && (
        <form onSubmit={handleNaturalSubmit} className="flex gap-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='Try: "Find Data Engineer jobs in Chennai posted within 24 hours requiring Python and AWS"'
            className="flex-1 border border-slate-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg font-medium text-sm transition-colors flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            Search
          </button>
        </form>
      )}

      {mode === 'structured' && (
        <p className="text-sm text-slate-500">Use the filters panel on the left to configure your search, then click Search.</p>
      )}
    </div>
  )
}

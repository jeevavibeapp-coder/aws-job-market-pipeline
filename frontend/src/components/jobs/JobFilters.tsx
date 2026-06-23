'use client'
import { useState } from 'react'
import type { SearchRequest } from '@/types'

interface Props {
  onSearch: (req: SearchRequest) => void
}

export default function JobFilters({ onSearch }: Props) {
  const [role, setRole] = useState('')
  const [experience, setExperience] = useState(2)
  const [skillInput, setSkillInput] = useState('')
  const [skills, setSkills] = useState<string[]>([])
  const [locationInput, setLocationInput] = useState('')
  const [locations, setLocations] = useState<string[]>([])
  const [remoteType, setRemoteType] = useState<string[]>([])
  const [postedWithin, setPostedWithin] = useState(24)
  const [minScore, setMinScore] = useState(70)
  const [tolerance, setTolerance] = useState(1.0)

  const addSkill = () => {
    const s = skillInput.trim()
    if (s && !skills.includes(s)) setSkills([...skills, s])
    setSkillInput('')
  }

  const addLocation = () => {
    const l = locationInput.trim()
    if (l && !locations.includes(l)) setLocations([...locations, l])
    setLocationInput('')
  }

  const toggleRemote = (v: string) =>
    setRemoteType((prev) => prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v])

  const handleSearch = () => {
    if (!role.trim()) return alert('Please enter a target role')
    onSearch({
      target_role: role,
      experience_years: experience,
      skills,
      locations,
      remote_type: remoteType,
      posted_within_hours: postedWithin,
      min_score: minScore,
      experience_tolerance: tolerance,
      max_results: 50,
    })
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-5 sticky top-0">
      <h3 className="font-semibold text-slate-900">Search Filters</h3>

      <div>
        <label className="text-xs font-medium text-slate-600 uppercase tracking-wide">Target Role</label>
        <input
          value={role}
          onChange={(e) => setRole(e.target.value)}
          placeholder="e.g. Data Engineer"
          className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="text-xs font-medium text-slate-600 uppercase tracking-wide">
          Experience: <span className="text-blue-600">{experience} yrs</span>
        </label>
        <input
          type="range" min={0} max={15} step={0.5}
          value={experience} onChange={(e) => setExperience(Number(e.target.value))}
          className="mt-1 w-full"
        />
        <div className="flex justify-between text-xs text-slate-400"><span>0</span><span>15</span></div>
      </div>

      <div>
        <label className="text-xs font-medium text-slate-600 uppercase tracking-wide">Skills</label>
        <div className="flex gap-2 mt-1">
          <input
            value={skillInput} onChange={(e) => setSkillInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSkill())}
            placeholder="Python, AWS..."
            className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button onClick={addSkill} className="px-3 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm font-medium">+</button>
        </div>
        {skills.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {skills.map((s) => (
              <span key={s} className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 text-xs px-2 py-1 rounded-full">
                {s}
                <button onClick={() => setSkills(skills.filter((x) => x !== s))} className="hover:text-blue-900">×</button>
              </span>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="text-xs font-medium text-slate-600 uppercase tracking-wide">Locations</label>
        <div className="flex gap-2 mt-1">
          <input
            value={locationInput} onChange={(e) => setLocationInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addLocation())}
            placeholder="Chennai, Bangalore..."
            className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button onClick={addLocation} className="px-3 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm font-medium">+</button>
        </div>
        {locations.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {locations.map((l) => (
              <span key={l} className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 text-xs px-2 py-1 rounded-full">
                {l}
                <button onClick={() => setLocations(locations.filter((x) => x !== l))}>×</button>
              </span>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="text-xs font-medium text-slate-600 uppercase tracking-wide">Work Mode</label>
        <div className="flex gap-2 mt-1">
          {['remote', 'hybrid', 'onsite'].map((v) => (
            <button
              key={v} onClick={() => toggleRemote(v)}
              className={`flex-1 py-1.5 text-xs rounded-lg border font-medium capitalize transition-colors ${
                remoteType.includes(v)
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'border-slate-300 text-slate-600 hover:border-slate-400'
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-xs font-medium text-slate-600 uppercase tracking-wide">Posted Within</label>
        <div className="grid grid-cols-2 gap-1.5 mt-1">
          {[{ label: '24 hours', value: 24 }, { label: '3 days', value: 72 }, { label: '7 days', value: 168 }, { label: '14 days', value: 336 }].map(({ label, value }) => (
            <button
              key={value} onClick={() => setPostedWithin(value)}
              className={`py-1.5 text-xs rounded-lg border font-medium transition-colors ${
                postedWithin === value ? 'bg-blue-600 text-white border-blue-600' : 'border-slate-300 text-slate-600'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="text-xs font-medium text-slate-600 uppercase tracking-wide">
          Min Score: <span className="text-blue-600">{minScore}</span>
        </label>
        <input
          type="range" min={50} max={100} value={minScore}
          onChange={(e) => setMinScore(Number(e.target.value))}
          className="mt-1 w-full"
        />
      </div>

      <div>
        <label className="text-xs font-medium text-slate-600 uppercase tracking-wide">
          Exp. tolerance: <span className="text-blue-600">+{tolerance} yr</span>
        </label>
        <input
          type="range" min={0} max={3} step={0.5} value={tolerance}
          onChange={(e) => setTolerance(Number(e.target.value))}
          className="mt-1 w-full"
        />
      </div>

      <button
        onClick={handleSearch}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded-lg font-medium transition-colors"
      >
        Search Jobs
      </button>
    </div>
  )
}

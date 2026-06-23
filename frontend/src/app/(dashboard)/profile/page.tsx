'use client'
import { useEffect, useState, useRef } from 'react'
import { resumeApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { ResumeProfile } from '@/types'
import { Upload, Loader2, User, CheckCircle2 } from 'lucide-react'

export default function ProfilePage() {
  const { user } = useAuth()
  const [profile, setProfile] = useState<ResumeProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    resumeApi.get()
      .then(setProfile)
      .catch(() => setProfile(null))
      .finally(() => setLoading(false))
  }, [])

  const handleFile = async (file: File) => {
    setUploading(true)
    setUploadSuccess(false)
    try {
      await resumeApi.upload(file)
      const updated = await resumeApi.get()
      setProfile(updated)
      setUploadSuccess(true)
      setTimeout(() => setUploadSuccess(false), 3000)
    } catch (e) {
      console.error(e)
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <User className="w-5 h-5" /> Account Info
        </h2>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-slate-500">Full name</label>
            <p className="text-slate-900 font-medium">{user?.full_name}</p>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-500">Email</label>
            <p className="text-slate-900">{user?.email}</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <Upload className="w-5 h-5" /> Resume
        </h2>

        {uploadSuccess && (
          <div className="flex items-center gap-2 bg-green-50 border border-green-200 text-green-700 rounded-lg px-4 py-3 mb-4 text-sm">
            <CheckCircle2 className="w-4 h-4" />
            Resume uploaded and parsed successfully!
          </div>
        )}

        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
            dragOver ? 'border-blue-400 bg-blue-50' : 'border-slate-300 hover:border-slate-400'
          }`}
        >
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
              <p className="text-sm text-slate-600">Parsing resume with AI...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="w-8 h-8 text-slate-400" />
              <p className="font-medium text-slate-700">Drop your resume here or click to browse</p>
              <p className="text-sm text-slate-400">PDF or DOCX, max 10MB</p>
            </div>
          )}
        </div>
        <input ref={fileRef} type="file" accept=".pdf,.docx" className="hidden" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
      </div>

      {profile && (
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h2 className="font-semibold text-slate-900 mb-4">Parsed Profile</h2>

          <div className="space-y-4">
            {profile.experience_years && (
              <div>
                <p className="text-xs font-medium text-slate-500 mb-1">Experience</p>
                <p className="font-semibold text-blue-700">{profile.experience_years} years</p>
              </div>
            )}

            {profile.parsed_skills.length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-500 mb-2">Skills ({profile.parsed_skills.length})</p>
                <div className="flex flex-wrap gap-1.5">
                  {profile.parsed_skills.map((s) => (
                    <span key={s} className="text-xs bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full font-medium">{s}</span>
                  ))}
                </div>
              </div>
            )}

            {profile.certifications.length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-500 mb-2">Certifications</p>
                <div className="space-y-1">
                  {profile.certifications.map((c) => (
                    <p key={typeof c === 'string' ? c : JSON.stringify(c)} className="text-sm text-slate-700">• {typeof c === 'string' ? c : JSON.stringify(c)}</p>
                  ))}
                </div>
              </div>
            )}

            {profile.education.length > 0 && (
              <div>
                <p className="text-xs font-medium text-slate-500 mb-2">Education</p>
                <div className="space-y-1">
                  {profile.education.map((e, i) => (
                    <p key={i} className="text-sm text-slate-700">{e.degree} — {e.institution} {e.year && `(${e.year})`}</p>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

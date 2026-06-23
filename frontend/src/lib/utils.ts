import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffHours < 1) return 'Just posted'
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return `${Math.floor(diffDays / 7)}w ago`
}

export function formatSalary(min?: number, max?: number, currency = 'INR'): string {
  if (!min && !max) return ''
  const fmt = (n: number) => currency === 'INR'
    ? `₹${(n / 100000).toFixed(1)}L`
    : `$${(n / 1000).toFixed(0)}k`
  if (min && max) return `${fmt(min)} - ${fmt(max)}`
  if (min) return `${fmt(min)}+`
  return `Up to ${fmt(max!)}`
}

export function scoreColor(score: number): string {
  if (score >= 85) return 'text-green-600'
  if (score >= 70) return 'text-yellow-600'
  return 'text-red-500'
}

export function scoreBg(score: number): string {
  if (score >= 85) return 'bg-green-100 text-green-800'
  if (score >= 70) return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

export function competitionLabel(score?: number): { label: string; color: string } {
  if (score === undefined) return { label: 'Unknown', color: 'bg-gray-100 text-gray-600' }
  if (score <= 25) return { label: 'Low', color: 'bg-green-100 text-green-700' }
  if (score <= 60) return { label: 'Medium', color: 'bg-yellow-100 text-yellow-700' }
  return { label: 'High', color: 'bg-red-100 text-red-700' }
}

export function sourceLabel(source: string): { label: string; color: string } {
  const map: Record<string, { label: string; color: string }> = {
    company_site: { label: 'Company Site', color: 'bg-green-100 text-green-800' },
    greenhouse: { label: 'Greenhouse', color: 'bg-blue-100 text-blue-800' },
    lever: { label: 'Lever', color: 'bg-purple-100 text-purple-800' },
    workday: { label: 'Workday', color: 'bg-indigo-100 text-indigo-800' },
    indeed: { label: 'Indeed', color: 'bg-orange-100 text-orange-800' },
    linkedin: { label: 'LinkedIn', color: 'bg-sky-100 text-sky-800' },
    jsearch: { label: 'JSearch', color: 'bg-gray-100 text-gray-800' },
  }
  return map[source] || { label: source, color: 'bg-gray-100 text-gray-800' }
}

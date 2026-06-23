export interface User {
  id: string
  email: string
  full_name: string
  is_active: boolean
  is_verified: boolean
  created_at: string
}

export interface Company {
  id: string
  name: string
  website?: string
  career_page_url?: string
  logo_url?: string
}

export type JobSource = 'company_site' | 'greenhouse' | 'lever' | 'workday' | 'indeed' | 'linkedin' | 'jsearch'
export type RemoteType = 'remote' | 'hybrid' | 'onsite'
export type SeniorityLevel = 'intern' | 'junior' | 'mid' | 'senior' | 'lead' | 'principal' | 'director'
export type ExperienceStatus = 'accept' | 'warning' | 'reject'

export interface JobScore {
  skill_match: number
  experience_match: number
  location_match: number
  technology_match: number
  seniority_match: number
  overall_score: number
  experience_status: ExperienceStatus
  match_reasons: string[]
  insight: string | null
}

export interface Job {
  id: string
  title: string
  company: Company
  location?: string
  remote_type: RemoteType
  experience_min?: number
  experience_max?: number
  salary_min?: number
  salary_max?: number
  currency?: string
  source: JobSource
  direct_apply_url?: string
  company_apply_url?: string
  job_url: string
  posted_at?: string
  scraped_at?: string
  applicant_count?: number
  competition_score?: number
  skills_required: string[]
  seniority_level?: SeniorityLevel
  description?: string
  requirements?: string
  score?: JobScore
}

export type ApplicationStatus =
  | 'saved'
  | 'applied'
  | 'interview_scheduled'
  | 'offer_received'
  | 'rejected'
  | 'withdrawn'

export interface Application {
  id: string
  job: Job
  status: ApplicationStatus
  applied_at?: string
  notes?: string
  created_at: string
  updated_at: string
}

export interface ApplicationStats {
  total: number
  saved: number
  applied: number
  interview_scheduled: number
  offer_received: number
  rejected: number
  withdrawn: number
}

export interface SearchRequest {
  query?: string
  target_role: string
  experience_years: number
  skills: string[]
  locations: string[]
  remote_type: string[]
  posted_within_hours: number
  min_score: number
  experience_tolerance: number
  max_results: number
  sources?: string[]
  competition_max?: number
}

export interface SearchResult {
  total: number
  results: Job[]
  search_params?: SearchRequest
  processing_time_ms: number
}

export interface DashboardStats {
  new_jobs_today: number
  high_match_jobs: number
  direct_apply_jobs: number
  applications_sent: number
  interviews_scheduled: number
}

export interface ResumeProfile {
  id: string
  user_id: string
  parsed_skills: string[]
  experience_years?: number
  education: Array<{ degree: string; institution: string; year?: string }>
  certifications: string[]
  projects: Array<{ name: string; description: string; technologies: string[] }>
  target_roles: string[]
  preferred_locations: string[]
  remote_preference?: RemoteType
  min_salary?: number
  resume_file_url?: string
  updated_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

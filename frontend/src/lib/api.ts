import axios from 'axios'
import type { Job, SearchRequest, SearchResult, Application, ApplicationStats, ResumeProfile, TokenResponse } from '@/types'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  register: (data: { email: string; password: string; full_name: string }) =>
    api.post<TokenResponse>('/api/v1/auth/register', data).then((r) => r.data),
  login: (data: { email: string; password: string }) =>
    api.post<TokenResponse>('/api/v1/auth/login', data).then((r) => r.data),
  me: () => api.get('/api/v1/auth/me').then((r) => r.data),
}

export const jobsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get<Job[]>('/api/v1/jobs', { params }).then((r) => r.data),
  get: (id: string) => api.get<Job>(`/api/v1/jobs/${id}`).then((r) => r.data),
  stats: () => api.get('/api/v1/jobs/stats').then((r) => r.data),
}

export const searchApi = {
  search: (req: SearchRequest) =>
    api.post<SearchResult>('/api/v1/search', req).then((r) => r.data),
  natural: (query: string, max_results = 50) =>
    api.post<SearchResult>('/api/v1/search/natural', { query, max_results }).then((r) => r.data),
}

export const applicationsApi = {
  list: (status?: string) =>
    api.get<Application[]>('/api/v1/applications', { params: status ? { status } : {} }).then((r) => r.data),
  create: (job_id: string, status = 'saved') =>
    api.post<Application>('/api/v1/applications', { job_id, status }).then((r) => r.data),
  update: (id: string, data: { status?: string; notes?: string }) =>
    api.put<Application>(`/api/v1/applications/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/api/v1/applications/${id}`),
  stats: () => api.get<ApplicationStats>('/api/v1/applications/stats').then((r) => r.data),
}

export const bookmarksApi = {
  list: () => api.get<Job[]>('/api/v1/bookmarks').then((r) => r.data),
  save: (job_id: string) => api.post(`/api/v1/bookmarks/${job_id}`).then((r) => r.data),
  remove: (job_id: string) => api.delete(`/api/v1/bookmarks/${job_id}`),
}

export const resumeApi = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/api/v1/resume/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } }).then((r) => r.data)
  },
  get: () => api.get<ResumeProfile>('/api/v1/resume').then((r) => r.data),
  updateProfile: (data: Partial<ResumeProfile>) =>
    api.put('/api/v1/resume/profile', data).then((r) => r.data),
}

export default api

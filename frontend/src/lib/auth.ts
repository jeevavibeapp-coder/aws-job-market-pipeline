'use client'
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@/types'
import { authApi } from './api'

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, full_name: string) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,

      login: async (email, password) => {
        set({ isLoading: true })
        try {
          const data = await authApi.login({ email, password })
          localStorage.setItem('access_token', data.access_token)
          set({ user: data.user, token: data.access_token, isLoading: false })
        } catch (e) {
          set({ isLoading: false })
          throw e
        }
      },

      register: async (email, password, full_name) => {
        set({ isLoading: true })
        try {
          const data = await authApi.register({ email, password, full_name })
          localStorage.setItem('access_token', data.access_token)
          set({ user: data.user, token: data.access_token, isLoading: false })
        } catch (e) {
          set({ isLoading: false })
          throw e
        }
      },

      logout: () => {
        localStorage.removeItem('access_token')
        set({ user: null, token: null })
      },

      loadUser: async () => {
        const token = localStorage.getItem('access_token')
        if (!token) return
        try {
          const user = await authApi.me()
          set({ user, token })
        } catch {
          set({ user: null, token: null })
        }
      },
    }),
    { name: 'auth-storage', partialize: (s) => ({ user: s.user, token: s.token }) }
  )
)

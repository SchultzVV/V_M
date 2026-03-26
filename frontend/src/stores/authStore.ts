import { create } from 'zustand'
import { authService } from '../services/authService'

export interface User {
  id: string
  username: string
}

interface AuthStore {
  user: User | null
  token: string | null
  isLoading: boolean
  error: string | null
  
  // Actions
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  validateToken: () => Promise<boolean>
  clearError: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: localStorage.getItem('token'),
  isLoading: false,
  error: null,

  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await authService.login({ username, password })
      set({
        token: response.access_token,
        user: response.user || null,
        isLoading: false,
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Login failed'
      set({
        error: message,
        isLoading: false,
      })
      throw error
    }
  },

  logout: () => {
    authService.logout()
    set({
      user: null,
      token: null,
      error: null,
    })
  },

  validateToken: async () => {
    try {
      const response = await authService.validateToken()
      if (response.valid) {
        set({ user: response.user || null })
        return true
      }
      return false
    } catch {
      set({ user: null, token: null })
      return false
    }
  },

  clearError: () => {
    set({ error: null })
  },
}))

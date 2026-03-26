import api from './api'

export interface LoginRequest {
  username: string
  password: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  user?: {
    id: string
    username: string
  }
}

export interface TokenValidationResponse {
  valid: boolean
  user?: {
    id: string
    username: string
  }
}

export const authService = {
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    try {
      const response = await api.post<AuthResponse>('/auth/admin/login', credentials)
      const { access_token } = response.data
      localStorage.setItem('token', access_token)
      return response.data
    } catch (error) {
      console.error('Login error:', error)
      throw error
    }
  },

  async validateToken(): Promise<TokenValidationResponse> {
    try {
      const response = await api.post<TokenValidationResponse>('/auth/token/validate')
      return response.data
    } catch (error) {
      localStorage.removeItem('token')
      throw error
    }
  },

  logout(): void {
    localStorage.removeItem('token')
  },

  getToken(): string | null {
    return localStorage.getItem('token')
  },

  isAuthenticated(): boolean {
    return !!this.getToken()
  },
}

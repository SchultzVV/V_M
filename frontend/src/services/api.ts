import axios, { AxiosInstance } from 'axios'

// Backend roda em HTTPS (com certificado self-signed)
// Vite proxy intercepta /api/* e encaminha para https://localhost:5000
// Deixamos baseURL vazio para que o proxy funcione
const api: AxiosInstance = axios.create({
  baseURL: '', // Vazio para proxy interceptar /api/... corretamente
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests if available
api.interceptors.request.use(
  (config) => {
    console.log(`[api.request] ${config.method?.toUpperCase()} ${config.url}`)
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    console.error('[api.request] ❌ Request error:', error)
    return Promise.reject(error)
  }
)

// Handle responses
api.interceptors.response.use(
  (response) => {
    console.log(`[api.response] ✅ ${response.status} ${response.config.url}`)
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      console.warn('[api.response] 🔑 Unauthorized (401), redirecting to login')
      localStorage.removeItem('token')
      window.location.href = '/admin/login'
    } else if (error.message === 'Network Error') {
      console.error('[api.response] ❌ Network Error - Cannot reach backend')
      console.error('   Ensure backend is running on: https://localhost:5000')
    } else if (error.code === 'ERR_BAD_REQUEST' || error.code === 'ERR_NETWORK') {
      console.error('[api.response] ❌ Connection error:', error.message)
    } else {
      console.error('[api.response] ❌ Error:', error.response?.status, error.message)
    }
    return Promise.reject(error)
  }
)

export default api

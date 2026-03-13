import axios from 'axios'
import type { AxiosInstance } from 'axios'

let refreshingPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshingPromise) {
    refreshingPromise = (async () => {
      try {
        const { data } = await api.post<{ access_token: string }>('/api/v1/auth/refresh')
        if (data?.access_token) {
          localStorage.setItem('access_token', data.access_token)
          return data.access_token
        }
        return null
      } catch {
        localStorage.removeItem('access_token')
        return null
      } finally {
        refreshingPromise = null
      }
    })()
  }
  return refreshingPromise
}

const api: AxiosInstance = axios.create({
  baseURL: (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

// Request interceptor - inject access token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor - handle 401 by clearing session
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as { _retry?: boolean; headers?: Record<string, string> }
    if (error.response?.status === 401 && !originalRequest?._retry) {
      originalRequest._retry = true
      const newAccessToken = await refreshAccessToken()
      if (newAccessToken) {
        originalRequest.headers = originalRequest.headers ?? {}
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        return api.request(originalRequest)
      }

      localStorage.removeItem('access_token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api

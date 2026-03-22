import axios from 'axios'
import type { AxiosInstance } from 'axios'

let refreshingPromise: Promise<string | null> | null = null

function resolveApiBaseUrl(): string {
  const configured = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
  const fallback = import.meta.env.DEV
    ? 'http://localhost:8000'
    : (typeof window !== 'undefined' ? window.location.origin : 'https://localhost')
  const selected = configured || fallback

  if (!import.meta.env.DEV) {
    try {
      const parsed = new URL(selected)
      const isLocalHost = ['localhost', '127.0.0.1', '10.0.2.2'].includes(parsed.hostname)
      if (parsed.protocol === 'http:' && !isLocalHost) {
        throw new Error('VITE_API_URL must use HTTPS in production builds')
      }
    } catch {
      throw new Error('Invalid API URL configuration for production build')
    }
  }

  return selected
}

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
  baseURL: resolveApiBaseUrl(),
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

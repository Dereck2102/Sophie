import axios from 'axios'
import type { AxiosInstance } from 'axios'

let refreshingPromise: Promise<string | null> | null = null

const TENANT_ERP_PREFIXES = [
  'dashboard',
  'clientes',
  'ventas',
  'compras',
  'inventario',
  'tickets',
  'proyectos',
  'boveda',
  'configuracion',
  'caja-chica',
  'caja_chica',
]

const TENANT_USERS_EXACT = new Set([
  '/api/v1/usuarios',
  '/api/v1/usuarios/',
  '/api/v1/usuarios/capacidad',
])

function getActiveEmpresaIdFromPath(): string | null {
  if (typeof window === 'undefined') return null
  const match = window.location.pathname.match(/^\/empresas\/(\d+)/)
  return match?.[1] ?? null
}

function shouldTenantPrefix(pathOnly: string): boolean {
  if (TENANT_USERS_EXACT.has(pathOnly)) return true
  return TENANT_ERP_PREFIXES.some((prefix) => pathOnly === `/api/v1/${prefix}` || pathOnly.startsWith(`/api/v1/${prefix}/`))
}

function applyTenantPrefixIfNeeded(rawUrl: string | undefined): string | undefined {
  if (!rawUrl) return rawUrl
  if (/^https?:\/\//i.test(rawUrl)) return rawUrl
  if (!rawUrl.startsWith('/api/v1/')) return rawUrl
  if (rawUrl.startsWith('/api/v1/empresas/')) return rawUrl
  if (rawUrl.startsWith('/api/v1/auth') || rawUrl.startsWith('/api/v1/public') || rawUrl.startsWith('/api/v1/global') || rawUrl.startsWith('/api/v1/admin') || rawUrl.startsWith('/api/v1/subscriptions')) {
    return rawUrl
  }

  const empresaId = getActiveEmpresaIdFromPath()
  if (!empresaId) return rawUrl

  const parts = rawUrl.split('?', 2)
  const pathOnly = parts[0] ?? ''
  const query = parts[1] ?? ''
  if (!shouldTenantPrefix(pathOnly)) return rawUrl

  const tenantPath = `/api/v1/empresas/${empresaId}${pathOnly.replace('/api/v1', '')}`
  return query ? `${tenantPath}?${query}` : tenantPath
}

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
  config.url = applyTenantPrefixIfNeeded(config.url)
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

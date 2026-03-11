import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../services/api'
import type { Usuario, LoginRequest, TokenResponse } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<Usuario | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const mfaRequired = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)

  async function login(credentials: LoginRequest): Promise<boolean> {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.post<TokenResponse>('/api/v1/auth/login', credentials)
      if (data.mfa_required) {
        mfaRequired.value = true
        return false
      }
      accessToken.value = data.access_token
      localStorage.setItem('access_token', data.access_token)
      await fetchMe()
      return true
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      error.value = err.response?.data?.detail ?? 'Login failed'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchMe(): Promise<void> {
    try {
      const { data } = await api.get<Usuario>('/api/v1/usuarios/me')
      user.value = data
    } catch {
      logout()
    }
  }

  function logout(): void {
    user.value = null
    accessToken.value = null
    mfaRequired.value = false
    localStorage.removeItem('access_token')
    api.post('/api/v1/auth/logout').catch(() => {})
  }

  // Initialize on store creation
  if (accessToken.value) {
    fetchMe()
  }

  return { user, accessToken, mfaRequired, loading, error, isAuthenticated, login, fetchMe, logout }
})

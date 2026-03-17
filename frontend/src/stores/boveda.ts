import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'
import type { Credencial, CredencialCreatePayload, CredencialReveal, CredencialUpdatePayload } from '../types/boveda'

export const useBovedaStore = defineStore('boveda', () => {
  const credenciales = ref<Credencial[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const lastLoadedAt = ref<number | null>(null)
  const cacheMetrics = ref({ hits: 0, misses: 0, inFlightReuses: 0, networkLoads: 0 })
  let fetchRequest: Promise<void> | null = null

  async function fetchCredenciales(force = false): Promise<void> {
    if (!force && lastLoadedAt.value && Date.now() - lastLoadedAt.value < 60_000) {
      cacheMetrics.value.hits += 1
      return
    }
    cacheMetrics.value.misses += 1
    if (fetchRequest) {
      cacheMetrics.value.inFlightReuses += 1
      return fetchRequest
    }

    loading.value = true
    error.value = null
    cacheMetrics.value.networkLoads += 1
    fetchRequest = (async () => {
      try {
        const { data } = await api.get<Credencial[]>('/api/v1/boveda/')
        credenciales.value = data
        lastLoadedAt.value = Date.now()
      } catch (e: unknown) {
        const err = e as { response?: { data?: { detail?: string } }; message?: string }
        error.value = err.response?.data?.detail ?? err.message ?? 'No se pudo cargar la bóveda'
        throw e
      } finally {
        loading.value = false
        fetchRequest = null
      }
    })()

    return fetchRequest
  }

  async function createCredencial(payload: CredencialCreatePayload): Promise<Credencial> {
    error.value = null
    try {
      const { data } = await api.post<Credencial>('/api/v1/boveda/', payload)
      credenciales.value.unshift(data)
      lastLoadedAt.value = Date.now()
      return data
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      error.value = err.response?.data?.detail ?? err.message ?? 'No se pudo crear la credencial'
      throw e
    }
  }

  async function updateCredencial(id: number, payload: CredencialUpdatePayload): Promise<Credencial> {
    error.value = null
    try {
      const { data } = await api.patch<Credencial>(`/api/v1/boveda/${id}`, payload)
      const idx = credenciales.value.findIndex((credencial) => credencial.id_credencial === id)
      if (idx >= 0) credenciales.value[idx] = data
      lastLoadedAt.value = Date.now()
      return data
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      error.value = err.response?.data?.detail ?? err.message ?? 'No se pudo actualizar la credencial'
      throw e
    }
  }

  async function deleteCredencial(id: number): Promise<void> {
    error.value = null
    try {
      await api.delete(`/api/v1/boveda/${id}`)
      credenciales.value = credenciales.value.filter((credencial) => credencial.id_credencial !== id)
      lastLoadedAt.value = Date.now()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      error.value = err.response?.data?.detail ?? err.message ?? 'No se pudo eliminar la credencial'
      throw e
    }
  }

  async function revealCredencial(id: number): Promise<CredencialReveal> {
    error.value = null
    try {
      const { data } = await api.get<CredencialReveal>(`/api/v1/boveda/${id}/reveal`)
      return data
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      error.value = err.response?.data?.detail ?? err.message ?? 'No se pudo revelar la credencial'
      throw e
    }
  }

  function clearError(): void {
    error.value = null
  }

  function resetCacheMetrics(): void {
    cacheMetrics.value = { hits: 0, misses: 0, inFlightReuses: 0, networkLoads: 0 }
  }

  return {
    credenciales,
    loading,
    error,
    lastLoadedAt,
    cacheMetrics,
    resetCacheMetrics,
    fetchCredenciales,
    createCredencial,
    updateCredencial,
    deleteCredencial,
    revealCredencial,
    clearError,
  }
})

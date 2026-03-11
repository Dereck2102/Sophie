import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'
import type { Cliente, EventoCliente } from '../types'

export const useClienteStore = defineStore('clientes', () => {
  const clientes = ref<Cliente[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchClientes(tipo?: 'B2B' | 'B2C'): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const params = tipo ? { tipo } : {}
      const { data } = await api.get<Cliente[]>('/api/v1/clientes/', { params })
      clientes.value = data
    } catch (e: unknown) {
      const err = e as { message?: string }
      error.value = err.message ?? 'Error fetching clients'
    } finally {
      loading.value = false
    }
  }

  async function fetchCliente(id: number): Promise<Cliente | null> {
    try {
      const { data } = await api.get<Cliente>(`/api/v1/clientes/${id}`)
      return data
    } catch {
      return null
    }
  }

  async function createCliente(payload: unknown): Promise<Cliente> {
    const { data } = await api.post<Cliente>('/api/v1/clientes/', payload)
    clientes.value.unshift(data)
    return data
  }

  async function updateCliente(id: number, payload: unknown): Promise<Cliente> {
    const { data } = await api.put<Cliente>(`/api/v1/clientes/${id}`, payload)
    const idx = clientes.value.findIndex((c) => c.id_cliente === id)
    if (idx >= 0) clientes.value[idx] = data
    return data
  }

  async function fetchTimeline(id: number): Promise<EventoCliente[]> {
    const { data } = await api.get<EventoCliente[]>(`/api/v1/clientes/${id}/timeline`)
    return data
  }

  return { clientes, loading, error, fetchClientes, fetchCliente, createCliente, updateCliente, fetchTimeline }
})

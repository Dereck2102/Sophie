import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'
import { useDashboardStore } from './dashboard'
import type { Reparacion, Ticket } from '../types'

export const useTicketStore = defineStore('tickets', () => {
  const dashboardStore = useDashboardStore()
  const tickets = ref<Ticket[]>([])
  const loading = ref(false)
  const lastLoadedAt = ref<number | null>(null)
  const cacheMetrics = ref({ hits: 0, misses: 0, inFlightReuses: 0, networkLoads: 0 })
  let fetchRequest: Promise<void> | null = null

  function invalidateDashboardKpis(options: { stats?: boolean; analytics?: boolean }): void {
    dashboardStore.invalidateCache(options)
  }

  function resetCacheMetrics(): void {
    cacheMetrics.value = { hits: 0, misses: 0, inFlightReuses: 0, networkLoads: 0 }
  }

  async function fetchTickets(force = false): Promise<void> {
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
    cacheMetrics.value.networkLoads += 1
    fetchRequest = (async () => {
      try {
        const { data } = await api.get<Ticket[]>('/api/v1/tickets/')
        tickets.value = data
        lastLoadedAt.value = Date.now()
      } finally {
        loading.value = false
        fetchRequest = null
      }
    })()

    return fetchRequest
  }

  async function createTicket(payload: unknown): Promise<Ticket> {
    const { data } = await api.post<Ticket>('/api/v1/tickets/', payload)
    tickets.value.unshift(data)
    invalidateDashboardKpis({ stats: true, analytics: false })
    return data
  }

  async function updateTicket(id: number, payload: unknown): Promise<Ticket> {
    const { data } = await api.patch<Ticket>(`/api/v1/tickets/${id}`, payload)
    const idx = tickets.value.findIndex((t) => t.id_ticket === id)
    if (idx >= 0) tickets.value[idx] = data
    invalidateDashboardKpis({ stats: true, analytics: true })
    return data
  }

  async function startTicket(id: number): Promise<Ticket> {
    const { data } = await api.post<Ticket>(`/api/v1/tickets/${id}/start`)
    const idx = tickets.value.findIndex((t) => t.id_ticket === id)
    if (idx >= 0) tickets.value[idx] = data
    invalidateDashboardKpis({ stats: true, analytics: false })
    return data
  }

  async function finishTicket(id: number): Promise<Ticket> {
    const { data } = await api.post<Ticket>(`/api/v1/tickets/${id}/finish`)
    const idx = tickets.value.findIndex((t) => t.id_ticket === id)
    if (idx >= 0) tickets.value[idx] = data
    invalidateDashboardKpis({ stats: true, analytics: true })
    return data
  }

  async function uploadFotos(id: number, files: File[]): Promise<Reparacion> {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    const { data } = await api.post<Reparacion>(`/api/v1/tickets/${id}/reparacion/fotos`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  }

  async function deleteTicket(id: number): Promise<void> {
    await api.delete(`/api/v1/tickets/${id}`)
    tickets.value = tickets.value.filter((t) => t.id_ticket !== id)
    invalidateDashboardKpis({ stats: true, analytics: true })
  }

  return { tickets, loading, cacheMetrics, resetCacheMetrics, fetchTickets, createTicket, updateTicket, startTicket, finishTicket, uploadFotos, deleteTicket }
})

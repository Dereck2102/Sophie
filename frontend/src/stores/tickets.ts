import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'
import type { Reparacion, Ticket } from '../types'

export const useTicketStore = defineStore('tickets', () => {
  const tickets = ref<Ticket[]>([])
  const loading = ref(false)

  async function fetchTickets(): Promise<void> {
    loading.value = true
    try {
      const { data } = await api.get<Ticket[]>('/api/v1/tickets/')
      tickets.value = data
    } finally {
      loading.value = false
    }
  }

  async function createTicket(payload: unknown): Promise<Ticket> {
    const { data } = await api.post<Ticket>('/api/v1/tickets/', payload)
    tickets.value.unshift(data)
    return data
  }

  async function updateTicket(id: number, payload: unknown): Promise<Ticket> {
    const { data } = await api.patch<Ticket>(`/api/v1/tickets/${id}`, payload)
    const idx = tickets.value.findIndex((t) => t.id_ticket === id)
    if (idx >= 0) tickets.value[idx] = data
    return data
  }

  async function startTicket(id: number): Promise<Ticket> {
    const { data } = await api.post<Ticket>(`/api/v1/tickets/${id}/start`)
    const idx = tickets.value.findIndex((t) => t.id_ticket === id)
    if (idx >= 0) tickets.value[idx] = data
    return data
  }

  async function finishTicket(id: number): Promise<Ticket> {
    const { data } = await api.post<Ticket>(`/api/v1/tickets/${id}/finish`)
    const idx = tickets.value.findIndex((t) => t.id_ticket === id)
    if (idx >= 0) tickets.value[idx] = data
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
  }

  return { tickets, loading, fetchTickets, createTicket, updateTicket, startTicket, finishTicket, uploadFotos, deleteTicket }
})

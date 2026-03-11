import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'
import type { Cotizacion } from '../types'

export const useVentasStore = defineStore('ventas', () => {
  const cotizaciones = ref<Cotizacion[]>([])
  const loading = ref(false)

  async function fetchCotizaciones(): Promise<void> {
    loading.value = true
    try {
      const { data } = await api.get<Cotizacion[]>('/api/v1/ventas/cotizaciones')
      cotizaciones.value = data
    } finally {
      loading.value = false
    }
  }

  async function createCotizacion(payload: unknown): Promise<Cotizacion> {
    const { data } = await api.post<Cotizacion>('/api/v1/ventas/cotizaciones', payload)
    cotizaciones.value.unshift(data)
    return data
  }

  async function updateEstado(id: number, estado: string): Promise<Cotizacion> {
    const { data } = await api.patch<Cotizacion>(`/api/v1/ventas/cotizaciones/${id}`, { estado })
    const idx = cotizaciones.value.findIndex((c) => c.id_cotizacion === id)
    if (idx >= 0) cotizaciones.value[idx] = data
    return data
  }

  async function facturar(id: number, numero_factura: string): Promise<void> {
    await api.post(`/api/v1/ventas/cotizaciones/${id}/facturar`, { numero_factura })
    await fetchCotizaciones()
  }

  return { cotizaciones, loading, fetchCotizaciones, createCotizacion, updateEstado, facturar }
})

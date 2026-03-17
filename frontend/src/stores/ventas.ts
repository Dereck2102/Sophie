import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'
import { useProyectoStore } from './proyectos'
import { useDashboardStore } from './dashboard'
import type { Cotizacion } from '../types'

export const useVentasStore = defineStore('ventas', () => {
  const proyectoStore = useProyectoStore()
  const dashboardStore = useDashboardStore()
  const cotizaciones = ref<Cotizacion[]>([])
  const loading = ref(false)
  const lastLoadedAt = ref<number | null>(null)
  const loadedLimit = ref<number>(0)
  const cacheMetrics = ref({ hits: 0, misses: 0, inFlightReuses: 0, networkLoads: 0 })
  let fetchRequest: Promise<void> | null = null
  let fetchRequestLimit = 0

  function invalidateProyectoCache(idProyecto?: number | null): void {
    if (!idProyecto) return
    proyectoStore.clearProyectoDetailCache(idProyecto)
  }

  function invalidateDashboardKpis(options: { stats?: boolean; analytics?: boolean }): void {
    dashboardStore.invalidateCache(options)
  }

  function resetCacheMetrics(): void {
    cacheMetrics.value = { hits: 0, misses: 0, inFlightReuses: 0, networkLoads: 0 }
  }

  async function fetchCotizaciones(force = false, limit = 50): Promise<void> {
    const isFresh = lastLoadedAt.value && Date.now() - lastLoadedAt.value < 60_000
    if (!force && isFresh && loadedLimit.value >= limit) {
      cacheMetrics.value.hits += 1
      return
    }

    cacheMetrics.value.misses += 1

    if (fetchRequest && fetchRequestLimit >= limit) {
      cacheMetrics.value.inFlightReuses += 1
      return fetchRequest
    }

    loading.value = true
    cacheMetrics.value.networkLoads += 1
    fetchRequestLimit = limit
    fetchRequest = (async () => {
      try {
        const { data } = await api.get<Cotizacion[]>('/api/v1/ventas/cotizaciones', {
          params: { limit },
        })
        cotizaciones.value = data
        lastLoadedAt.value = Date.now()
        loadedLimit.value = limit
      } finally {
        loading.value = false
        fetchRequest = null
        fetchRequestLimit = 0
      }
    })()

    return fetchRequest
  }

  async function createCotizacion(payload: unknown): Promise<Cotizacion> {
    const { data } = await api.post<Cotizacion>('/api/v1/ventas/cotizaciones', payload)
    cotizaciones.value.unshift(data)
    invalidateProyectoCache(data.id_proyecto)
    invalidateDashboardKpis({ stats: true, analytics: true })
    return data
  }

  async function updateEstado(id: number, estado: string): Promise<Cotizacion> {
    const { data } = await api.patch<Cotizacion>(`/api/v1/ventas/cotizaciones/${id}`, { estado })
    const idx = cotizaciones.value.findIndex((c) => c.id_cotizacion === id)
    if (idx >= 0) cotizaciones.value[idx] = data
    invalidateProyectoCache(data.id_proyecto)
    invalidateDashboardKpis({ stats: false, analytics: true })
    return data
  }

  async function facturar(id: number, numero_factura: string): Promise<void> {
    const current = cotizaciones.value.find((c) => c.id_cotizacion === id)
    await api.post(`/api/v1/ventas/cotizaciones/${id}/facturar`, { numero_factura })
    invalidateProyectoCache(current?.id_proyecto)
    invalidateDashboardKpis({ stats: true, analytics: true })
    await fetchCotizaciones(true, Math.max(loadedLimit.value, 50))
  }

  async function deleteCotizacion(id: number): Promise<void> {
    const current = cotizaciones.value.find((c) => c.id_cotizacion === id)
    await api.delete(`/api/v1/ventas/cotizaciones/${id}`)
    cotizaciones.value = cotizaciones.value.filter((c) => c.id_cotizacion !== id)
    invalidateProyectoCache(current?.id_proyecto)
    invalidateDashboardKpis({ stats: true, analytics: true })
  }

  return { cotizaciones, loading, lastLoadedAt, loadedLimit, cacheMetrics, resetCacheMetrics, fetchCotizaciones, createCotizacion, updateEstado, facturar, deleteCotizacion }
})

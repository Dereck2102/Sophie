import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'
import type { CotizacionProyectoResumen, Proyecto, ProyectoRentabilidad, Tarea } from '../types'

export const useProyectoStore = defineStore('proyectos', () => {
  const proyectos = ref<Proyecto[]>([])
  const tareas = ref<Tarea[]>([])
  const loading = ref(false)
  const lastLoadedAt = ref<number | null>(null)
  const tareasCacheByProyecto = ref<Record<number, Tarea[]>>({})
  const tareasCacheLoadedAt = ref<Record<number, number>>({})
  const cotizacionesCacheByProyecto = ref<Record<number, CotizacionProyectoResumen[]>>({})
  const cotizacionesCacheLoadedAt = ref<Record<number, number>>({})
  const rentabilidadCacheByProyecto = ref<Record<number, ProyectoRentabilidad>>({})
  const rentabilidadCacheLoadedAt = ref<Record<number, number>>({})
  const cacheMetrics = ref({
    proyectosHits: 0,
    proyectosMisses: 0,
    proyectosInFlightReuses: 0,
    proyectosNetworkLoads: 0,
    tareasHits: 0,
    tareasMisses: 0,
    tareasInFlightReuses: 0,
    tareasNetworkLoads: 0,
    cotizacionesHits: 0,
    cotizacionesMisses: 0,
    cotizacionesInFlightReuses: 0,
    cotizacionesNetworkLoads: 0,
    rentabilidadHits: 0,
    rentabilidadMisses: 0,
    rentabilidadInFlightReuses: 0,
    rentabilidadNetworkLoads: 0,
  })
  let fetchRequest: Promise<void> | null = null
  const tareasRequestByProyecto = new Map<number, Promise<Tarea[]>>()
  const cotizacionesRequestByProyecto = new Map<number, Promise<CotizacionProyectoResumen[]>>()
  const rentabilidadRequestByProyecto = new Map<number, Promise<ProyectoRentabilidad>>()

  function clearProyectoDetailCache(idProyecto: number): void {
    delete tareasCacheByProyecto.value[idProyecto]
    delete tareasCacheLoadedAt.value[idProyecto]
    delete cotizacionesCacheByProyecto.value[idProyecto]
    delete cotizacionesCacheLoadedAt.value[idProyecto]
    delete rentabilidadCacheByProyecto.value[idProyecto]
    delete rentabilidadCacheLoadedAt.value[idProyecto]
  }

  function resetCacheMetrics(): void {
    cacheMetrics.value = {
      proyectosHits: 0,
      proyectosMisses: 0,
      proyectosInFlightReuses: 0,
      proyectosNetworkLoads: 0,
      tareasHits: 0,
      tareasMisses: 0,
      tareasInFlightReuses: 0,
      tareasNetworkLoads: 0,
      cotizacionesHits: 0,
      cotizacionesMisses: 0,
      cotizacionesInFlightReuses: 0,
      cotizacionesNetworkLoads: 0,
      rentabilidadHits: 0,
      rentabilidadMisses: 0,
      rentabilidadInFlightReuses: 0,
      rentabilidadNetworkLoads: 0,
    }
  }

  async function fetchProyectos(force = false): Promise<void> {
    if (!force && lastLoadedAt.value && Date.now() - lastLoadedAt.value < 60_000) {
      cacheMetrics.value.proyectosHits += 1
      return
    }
    cacheMetrics.value.proyectosMisses += 1
    if (fetchRequest) {
      cacheMetrics.value.proyectosInFlightReuses += 1
      return fetchRequest
    }

    loading.value = true
    cacheMetrics.value.proyectosNetworkLoads += 1
    fetchRequest = (async () => {
      try {
        const { data } = await api.get<Proyecto[]>('/api/v1/proyectos/')
        proyectos.value = data
        lastLoadedAt.value = Date.now()
      } finally {
        loading.value = false
        fetchRequest = null
      }
    })()

    return fetchRequest
  }

  async function createProyecto(payload: unknown): Promise<Proyecto> {
    const { data } = await api.post<Proyecto>('/api/v1/proyectos/', payload)
    proyectos.value.unshift(data)
    return data
  }

  async function updateProyecto(id: number, payload: unknown): Promise<Proyecto> {
    const { data } = await api.patch<Proyecto>(`/api/v1/proyectos/${id}`, payload)
    const idx = proyectos.value.findIndex((p) => p.id_proyecto === id)
    if (idx >= 0) proyectos.value[idx] = data
    clearProyectoDetailCache(id)
    return data
  }

  async function deleteProyecto(id: number): Promise<void> {
    await api.delete(`/api/v1/proyectos/${id}`)
    proyectos.value = proyectos.value.filter((p) => p.id_proyecto !== id)
    clearProyectoDetailCache(id)
  }

  async function fetchTareas(idProyecto: number, force = false): Promise<Tarea[]> {
    const lastLoaded = tareasCacheLoadedAt.value[idProyecto]
    if (!force && lastLoaded && Date.now() - lastLoaded < 60_000) {
      cacheMetrics.value.tareasHits += 1
      const cached = tareasCacheByProyecto.value[idProyecto] ?? []
      tareas.value = [...cached]
      return [...cached]
    }
    cacheMetrics.value.tareasMisses += 1

    const inFlight = tareasRequestByProyecto.get(idProyecto)
    if (inFlight) {
      cacheMetrics.value.tareasInFlightReuses += 1
      return inFlight
    }

    const request = (async () => {
      cacheMetrics.value.tareasNetworkLoads += 1
      const { data } = await api.get<Tarea[]>(`/api/v1/proyectos/${idProyecto}/tareas`)
      tareasCacheByProyecto.value[idProyecto] = data
      tareasCacheLoadedAt.value[idProyecto] = Date.now()
      tareas.value = [...data]
      return [...data]
    })()

    tareasRequestByProyecto.set(idProyecto, request)
    try {
      return await request
    } finally {
      tareasRequestByProyecto.delete(idProyecto)
    }
  }

  async function fetchCotizacionesProyecto(idProyecto: number, force = false): Promise<CotizacionProyectoResumen[]> {
    const lastLoaded = cotizacionesCacheLoadedAt.value[idProyecto]
    if (!force && lastLoaded && Date.now() - lastLoaded < 60_000) {
      cacheMetrics.value.cotizacionesHits += 1
      return [...(cotizacionesCacheByProyecto.value[idProyecto] ?? [])]
    }
    cacheMetrics.value.cotizacionesMisses += 1

    const inFlight = cotizacionesRequestByProyecto.get(idProyecto)
    if (inFlight) {
      cacheMetrics.value.cotizacionesInFlightReuses += 1
      return inFlight
    }

    const request = (async () => {
      cacheMetrics.value.cotizacionesNetworkLoads += 1
      const { data } = await api.get<CotizacionProyectoResumen[]>(`/api/v1/proyectos/${idProyecto}/cotizaciones`)
      cotizacionesCacheByProyecto.value[idProyecto] = data
      cotizacionesCacheLoadedAt.value[idProyecto] = Date.now()
      return [...data]
    })()

    cotizacionesRequestByProyecto.set(idProyecto, request)
    try {
      return await request
    } finally {
      cotizacionesRequestByProyecto.delete(idProyecto)
    }
  }

  async function fetchRentabilidadProyecto(idProyecto: number, force = false): Promise<ProyectoRentabilidad> {
    const lastLoaded = rentabilidadCacheLoadedAt.value[idProyecto]
    if (!force && lastLoaded && Date.now() - lastLoaded < 60_000) {
      const cached = rentabilidadCacheByProyecto.value[idProyecto]
      if (cached) {
        cacheMetrics.value.rentabilidadHits += 1
        return { ...cached }
      }
    }
    cacheMetrics.value.rentabilidadMisses += 1

    const inFlight = rentabilidadRequestByProyecto.get(idProyecto)
    if (inFlight) {
      cacheMetrics.value.rentabilidadInFlightReuses += 1
      return inFlight
    }

    const request = (async () => {
      cacheMetrics.value.rentabilidadNetworkLoads += 1
      const { data } = await api.get<ProyectoRentabilidad>(`/api/v1/proyectos/${idProyecto}/rentabilidad`)
      rentabilidadCacheByProyecto.value[idProyecto] = data
      rentabilidadCacheLoadedAt.value[idProyecto] = Date.now()
      return { ...data }
    })()

    rentabilidadRequestByProyecto.set(idProyecto, request)
    try {
      return await request
    } finally {
      rentabilidadRequestByProyecto.delete(idProyecto)
    }
  }

  async function createTarea(idProyecto: number, payload: unknown): Promise<Tarea> {
    const { data } = await api.post<Tarea>(`/api/v1/proyectos/${idProyecto}/tareas`, payload)
    const current = tareasCacheByProyecto.value[idProyecto] ?? []
    tareasCacheByProyecto.value[idProyecto] = [...current, data]
    tareasCacheLoadedAt.value[idProyecto] = Date.now()
    tareas.value = [...tareasCacheByProyecto.value[idProyecto]]
    return data
  }

  async function updateTarea(id: number, payload: unknown): Promise<Tarea> {
    const { data } = await api.patch<Tarea>(`/api/v1/proyectos/tareas/${id}`, payload)
    const idx = tareas.value.findIndex((t) => t.id_tarea === id)
    if (idx >= 0) tareas.value[idx] = data

    for (const [idProyecto, list] of Object.entries(tareasCacheByProyecto.value)) {
      const projectId = Number(idProyecto)
      const taskIdx = list.findIndex((tarea) => tarea.id_tarea === id)
      if (taskIdx >= 0) {
        const updated = [...list]
        updated[taskIdx] = data
        tareasCacheByProyecto.value[projectId] = updated
        tareasCacheLoadedAt.value[projectId] = Date.now()
        break
      }
    }

    return data
  }

  async function deleteTarea(id: number): Promise<void> {
    await api.delete(`/api/v1/proyectos/tareas/${id}`)
    tareas.value = tareas.value.filter((t) => t.id_tarea !== id)

    for (const [idProyecto, list] of Object.entries(tareasCacheByProyecto.value)) {
      const projectId = Number(idProyecto)
      const filtered = list.filter((tarea) => tarea.id_tarea !== id)
      if (filtered.length !== list.length) {
        tareasCacheByProyecto.value[projectId] = filtered
        tareasCacheLoadedAt.value[projectId] = Date.now()
        break
      }
    }
  }

  return {
    proyectos,
    tareas,
    loading,
    lastLoadedAt,
    cacheMetrics,
    tareasCacheByProyecto,
    cotizacionesCacheByProyecto,
    rentabilidadCacheByProyecto,
    resetCacheMetrics,
    clearProyectoDetailCache,
    fetchProyectos,
    createProyecto,
    updateProyecto,
    deleteProyecto,
    fetchTareas,
    fetchCotizacionesProyecto,
    fetchRentabilidadProyecto,
    createTarea,
    updateTarea,
    deleteTarea,
  }
})

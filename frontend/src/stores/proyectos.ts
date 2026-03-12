import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'
import type { Proyecto, Tarea } from '../types'

export const useProyectoStore = defineStore('proyectos', () => {
  const proyectos = ref<Proyecto[]>([])
  const tareas = ref<Tarea[]>([])
  const loading = ref(false)

  async function fetchProyectos(): Promise<void> {
    loading.value = true
    try {
      const { data } = await api.get<Proyecto[]>('/api/v1/proyectos/')
      proyectos.value = data
    } finally {
      loading.value = false
    }
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
    return data
  }

  async function deleteProyecto(id: number): Promise<void> {
    await api.delete(`/api/v1/proyectos/${id}`)
    proyectos.value = proyectos.value.filter((p) => p.id_proyecto !== id)
  }

  async function fetchTareas(idProyecto: number): Promise<Tarea[]> {
    const { data } = await api.get<Tarea[]>(`/api/v1/proyectos/${idProyecto}/tareas`)
    tareas.value = data
    return data
  }

  async function createTarea(idProyecto: number, payload: unknown): Promise<Tarea> {
    const { data } = await api.post<Tarea>(`/api/v1/proyectos/${idProyecto}/tareas`, payload)
    tareas.value.unshift(data)
    return data
  }

  async function updateTarea(id: number, payload: unknown): Promise<Tarea> {
    const { data } = await api.patch<Tarea>(`/api/v1/proyectos/tareas/${id}`, payload)
    const idx = tareas.value.findIndex((t) => t.id_tarea === id)
    if (idx >= 0) tareas.value[idx] = data
    return data
  }

  async function deleteTarea(id: number): Promise<void> {
    await api.delete(`/api/v1/proyectos/tareas/${id}`)
    tareas.value = tareas.value.filter((t) => t.id_tarea !== id)
  }

  return {
    proyectos,
    tareas,
    loading,
    fetchProyectos,
    createProyecto,
    updateProyecto,
    deleteProyecto,
    fetchTareas,
    createTarea,
    updateTarea,
    deleteTarea,
  }
})

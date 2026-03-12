import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'
import type { Inventario, InventarioSerie, EstadoSerie } from '../types'

export const useInventarioStore = defineStore('inventario', () => {
  const productos = ref<Inventario[]>([])
  const series = ref<Record<number, InventarioSerie[]>>({})
  const loading = ref(false)

  async function fetchProductos(): Promise<void> {
    loading.value = true
    try {
      const { data } = await api.get<Inventario[]>('/api/v1/inventario/')
      productos.value = data
    } finally {
      loading.value = false
    }
  }

  async function createProducto(payload: unknown): Promise<Inventario> {
    const { data } = await api.post<Inventario>('/api/v1/inventario/', payload)
    productos.value.unshift(data)
    return data
  }

  async function updateProducto(id: number, payload: unknown): Promise<Inventario> {
    const { data } = await api.patch<Inventario>(`/api/v1/inventario/${id}`, payload)
    const idx = productos.value.findIndex((p) => p.id_producto === id)
    if (idx >= 0) productos.value[idx] = data
    return data
  }

  async function deleteProducto(id: number): Promise<void> {
    await api.delete(`/api/v1/inventario/${id}`)
    productos.value = productos.value.filter((p) => p.id_producto !== id)
    delete series.value[id]
  }

  async function fetchSeries(idProducto: number): Promise<InventarioSerie[]> {
    const { data } = await api.get<InventarioSerie[]>(`/api/v1/inventario/${idProducto}/series`)
    series.value[idProducto] = data
    return data
  }

  async function createSerie(payload: { id_producto: number; numero_serie: string; notas?: string }): Promise<InventarioSerie> {
    const { data } = await api.post<InventarioSerie>('/api/v1/inventario/series', payload)
    series.value[payload.id_producto] = [data, ...(series.value[payload.id_producto] ?? [])]
    const idx = productos.value.findIndex((p) => p.id_producto === payload.id_producto)
    if (idx >= 0) {
      const producto = productos.value[idx]
      if (producto) {
        productos.value[idx] = { ...producto, stock_actual: producto.stock_actual + 1 }
      }
    }
    return data
  }

  async function updateSerie(idSerie: number, payload: { estado: EstadoSerie; notas?: string }, idProducto: number): Promise<InventarioSerie> {
    const { data } = await api.patch<InventarioSerie>(`/api/v1/inventario/series/${idSerie}`, payload)
    const current = series.value[idProducto] ?? []
    const idx = current.findIndex((serie) => serie.id_serie === idSerie)
    if (idx >= 0) current[idx] = data
    return data
  }

  return { productos, series, loading, fetchProductos, createProducto, updateProducto, deleteProducto, fetchSeries, createSerie, updateSerie }
})

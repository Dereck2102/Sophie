import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'
import type { Inventario } from '../types'

export const useInventarioStore = defineStore('inventario', () => {
  const productos = ref<Inventario[]>([])
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

  return { productos, loading, fetchProductos, createProducto, updateProducto }
})

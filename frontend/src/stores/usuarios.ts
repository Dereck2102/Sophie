import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'
import type { TenantStaffingLimits, Usuario } from '../types'

export interface UsuarioCreate {
  username: string
  email: string
  password: string
  rol: Usuario['rol']
  nombre_completo?: string
  mfa_habilitado?: boolean
  force_mfa?: boolean
  permisos?: string[]
  vistas?: string[]
  herramientas?: string[]
}

export interface UsuarioUpdate {
  email?: string
  nombre_completo?: string
  activo?: boolean
  rol?: Usuario['rol']
  mfa_habilitado?: boolean
  force_mfa?: boolean
  permisos?: string[]
  vistas?: string[]
  herramientas?: string[]
}

export const useUsuarioStore = defineStore('usuarios', () => {
  const usuarios = ref<Usuario[]>([])
  const capacidad = ref<TenantStaffingLimits | null>(null)
  const loading = ref(false)
  const loadingCapacidad = ref(false)
  const error = ref<string | null>(null)

  async function fetchUsuarios(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get<Usuario[]>('/api/v1/usuarios/')
      usuarios.value = data
    } catch (e: unknown) {
      const err = e as { message?: string }
      error.value = err.message ?? 'Error al cargar usuarios'
    } finally {
      loading.value = false
    }
  }

  async function createUsuario(payload: UsuarioCreate): Promise<Usuario> {
    const { data } = await api.post<Usuario>('/api/v1/usuarios/', payload)
    usuarios.value.unshift(data)
    return data
  }

  async function updateUsuario(id: number, payload: UsuarioUpdate): Promise<Usuario> {
    const { data } = await api.patch<Usuario>(`/api/v1/usuarios/${id}`, payload)
    const idx = usuarios.value.findIndex((u) => u.id_usuario === id)
    if (idx >= 0) usuarios.value[idx] = data
    return data
  }

  async function deleteUsuario(id: number): Promise<void> {
    await api.delete(`/api/v1/usuarios/${id}`)
    usuarios.value = usuarios.value.filter((u) => u.id_usuario !== id)
  }

  async function fetchCapacidad(idCliente?: number): Promise<void> {
    loadingCapacidad.value = true
    error.value = null
    try {
      const { data } = await api.get<TenantStaffingLimits>('/api/v1/usuarios/capacidad', {
        params: idCliente ? { id_cliente: idCliente } : undefined,
      })
      capacidad.value = data
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      error.value = err.response?.data?.detail ?? err.message ?? 'Error al cargar capacidad por empresa'
      capacidad.value = null
    } finally {
      loadingCapacidad.value = false
    }
  }

  return {
    usuarios,
    capacidad,
    loading,
    loadingCapacidad,
    error,
    fetchUsuarios,
    fetchCapacidad,
    createUsuario,
    updateUsuario,
    deleteUsuario,
  }
})

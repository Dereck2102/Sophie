<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import api from '../services/api'
import type { GlobalCompanyUser, GlobalUserPasswordResetOut } from '../types'

const loading = ref(false)
const mutating = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)
const users = ref<GlobalCompanyUser[]>([])

async function loadUsers(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get<GlobalCompanyUser[]>('/api/v1/global/users', { params: { limit: 1500 } })
    users.value = data
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo cargar usuarios globales'
  } finally {
    loading.value = false
  }
}

async function toggleUser(user: GlobalCompanyUser): Promise<void> {
  mutating.value = true
  error.value = null
  success.value = null
  try {
    await api.patch(`/api/v1/global/users/${user.id_usuario}/activation`, { activo: !user.activo })
    success.value = `Usuario ${user.username} ${user.activo ? 'desactivado' : 'activado'}`
    await loadUsers()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo cambiar el estado del usuario'
  } finally {
    mutating.value = false
  }
}

async function forceReset(user: GlobalCompanyUser): Promise<void> {
  mutating.value = true
  error.value = null
  success.value = null
  try {
    const { data } = await api.post<GlobalUserPasswordResetOut>(`/api/v1/global/users/${user.id_usuario}/force-password-reset`)
    success.value = `Token temporal para ${user.username}: ${data.reset_token}`
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo forzar el reseteo de contraseña'
  } finally {
    mutating.value = false
  }
}

onMounted(() => {
  void loadUsers()
})
</script>

<template>
  <div class="space-y-6">
    <section class="rounded-2xl border border-gray-200 bg-white p-5">
      <h2 class="text-xl font-bold text-gray-900">Gestión Global de Usuarios</h2>
      <p class="text-sm text-gray-600 mt-1">Visión global por empresa y acciones de soporte de cuenta.</p>
    </section>

    <p v-if="error" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
    <p v-if="success" class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 break-all">{{ success }}</p>

    <Card title="Usuarios de todas las empresas" subtitle="SOPHIE ADMIN · Superadmin">
      <div v-if="loading" class="text-sm text-gray-500">Cargando usuarios...</div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left border-b border-gray-200">
              <th class="px-2 py-2">Usuario</th>
              <th class="px-2 py-2">Email</th>
              <th class="px-2 py-2">Empresa</th>
              <th class="px-2 py-2">Rol ERP</th>
              <th class="px-2 py-2">Estado</th>
              <th class="px-2 py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in users" :key="item.id_usuario" class="border-b border-gray-100">
              <td class="px-2 py-2 font-medium">{{ item.username }}</td>
              <td class="px-2 py-2">{{ item.email }}</td>
              <td class="px-2 py-2">{{ item.empresa_nombre ?? 'Global' }}</td>
              <td class="px-2 py-2 uppercase">{{ item.rol_fijo }}</td>
              <td class="px-2 py-2">
                <span :class="item.activo ? 'text-emerald-700' : 'text-amber-700'">{{ item.activo ? 'Activo' : 'Inactivo' }}</span>
              </td>
              <td class="px-2 py-2">
                <div class="flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" :disabled="mutating" @click="toggleUser(item)">
                    {{ item.activo ? 'Desactivar' : 'Activar' }}
                  </Button>
                  <Button size="sm" variant="secondary" :disabled="mutating" @click="forceReset(item)">Forzar reset</Button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>
  </div>
</template>

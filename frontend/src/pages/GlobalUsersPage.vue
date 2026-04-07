<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import api from '../services/api'
import type { GlobalCompanyUser, GlobalUserCreateIn, GlobalUserPasswordResetOut } from '../types'

const loading = ref(false)
const mutating = ref(false)
const creatingUser = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)
const createModalOpen = ref(false)

const users = ref<GlobalCompanyUser[]>([])

const createForm = ref<GlobalUserCreateIn>({
  username: '',
  email: '',
  password: '',
  nombre_completo: '',
  rol: 'agente_soporte',
})

function isStrongPassword(password: string): boolean {
  return password.length >= 8 && /\d/.test(password)
}

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

async function createUser(): Promise<void> {
  const trimmedUsername = createForm.value.username.trim()
  if (!trimmedUsername) {
    error.value = 'El username es obligatorio'
    return
  }
  if (!isStrongPassword(createForm.value.password)) {
    error.value = 'La contraseña debe tener al menos 8 caracteres y al menos un número'
    return
  }

  creatingUser.value = true
  error.value = null
  success.value = null
  try {
    await api.post('/api/v1/global/users', {
      ...createForm.value,
      username: trimmedUsername,
      nombre_completo: createForm.value.nombre_completo?.trim() || null,
    })
    success.value = `Usuario ${createForm.value.username} creado correctamente`
    createModalOpen.value = false
    createForm.value = {
      username: '',
      email: '',
      password: '',
      nombre_completo: '',
      rol: 'agente_soporte',
    }
    await loadUsers()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo crear el usuario maestro'
  } finally {
    creatingUser.value = false
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

async function deleteUser(user: GlobalCompanyUser): Promise<void> {
  if (!window.confirm(`¿Eliminar usuario ${user.username}? Esta acción no se puede deshacer.`)) return
  mutating.value = true
  error.value = null
  success.value = null
  try {
    await api.delete(`/api/v1/global/users/${user.id_usuario}`)
    success.value = `Usuario ${user.username} eliminado`
    await loadUsers()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo eliminar el usuario'
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
      <p class="text-sm text-gray-600 mt-1">Administra únicamente cuentas maestras y de soporte del Panel Maestro.</p>
      <div class="mt-4">
        <Button @click="createModalOpen = true">Crear usuario maestro</Button>
      </div>
    </section>

    <p v-if="error" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
    <p v-if="success" class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 break-all">{{ success }}</p>

    <Card title="Usuarios maestros" subtitle="SOPHIE ADMIN · Superadmin">
      <div v-if="loading" class="text-sm text-gray-500">Cargando usuarios...</div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left border-b border-gray-200">
              <th class="px-2 py-2">Usuario</th>
              <th class="px-2 py-2">Email</th>
              <th class="px-2 py-2">Empresa</th>
              <th class="px-2 py-2">Rol Maestro</th>
              <th class="px-2 py-2">Estado</th>
              <th class="px-2 py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in users"
              :key="item.id_usuario"
              class="border-b border-gray-100"
            >
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
                  <Button size="sm" variant="danger" :disabled="mutating" @click="deleteUser(item)">Eliminar</Button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>

    <Modal :open="createModalOpen" title="Crear usuario maestro" size="md" @close="createModalOpen = false">
      <form class="space-y-3" @submit.prevent="createUser">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Username</label>
          <input v-model="createForm.username" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" required />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input v-model="createForm.email" type="email" class="w-full rounded-lg border px-3 py-2 text-sm" required />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Nombre completo</label>
          <input v-model="createForm.nombre_completo" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Rol</label>
          <select v-model="createForm.rol" class="w-full rounded-lg border px-3 py-2 text-sm">
            <option value="agente_soporte">Agente de soporte</option>
            <option value="admin">Admin panel maestro</option>
          </select>
          <p class="mt-1 text-xs text-gray-500">El rol superadmin propietario se mantiene protegido por política del sistema.</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Password temporal</label>
          <input v-model="createForm.password" type="password" class="w-full rounded-lg border px-3 py-2 text-sm" required minlength="8" />
        </div>

        <div class="flex justify-end gap-2">
          <Button type="button" variant="secondary" @click="createModalOpen = false">Cancelar</Button>
          <Button type="submit" :loading="creatingUser">Crear usuario</Button>
        </div>
      </form>
    </Modal>
  </div>
</template>

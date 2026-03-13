<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Plus, Search, UserCog, ShieldCheck, Trash2 } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import { useUsuarioStore } from '../stores/usuarios'
import type { Usuario, RolEnum } from '../types'

const usuarioStore = useUsuarioStore()

const searchQuery = ref('')
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const selectedUser = ref<Usuario | null>(null)
const saving = ref(false)
const deleting = ref(false)
const formError = ref<string | null>(null)

const roles: RolEnum[] = [
  'superadmin',
  'ejecutivo',
  'administrativo_contable',
  'tecnico',
]

const roleLabels: Record<RolEnum, string> = {
  superadmin: 'Superadministrador',
  ejecutivo: 'Ejecutivo',
  administrativo_contable: 'Administrativo Contable',
  tecnico: 'Técnico',
}

interface AccessOption {
  value: string
  label: string
}

const permissionOptions: AccessOption[] = [
  { value: 'dashboard.view', label: 'Ver dashboard' },
  { value: 'clientes.manage', label: 'Gestionar clientes' },
  { value: 'ventas.manage', label: 'Gestionar ventas' },
  { value: 'compras.manage', label: 'Gestionar compras' },
  { value: 'proyectos.manage', label: 'Gestionar proyectos' },
  { value: 'tickets.manage', label: 'Gestionar tickets' },
  { value: 'inventario.read', label: 'Consultar inventario' },
  { value: 'reportes.view', label: 'Ver reportes' },
]

const viewOptions: AccessOption[] = [
  { value: 'dashboard', label: 'Dashboard' },
  { value: 'crm', label: 'CRM' },
  { value: 'ventas', label: 'Ventas' },
  { value: 'compras', label: 'Compras' },
  { value: 'proyectos', label: 'Proyectos' },
  { value: 'taller', label: 'Taller' },
  { value: 'inventario', label: 'Inventario' },
  { value: 'perfil', label: 'Perfil' },
  { value: 'boveda', label: 'Bóveda' },
  { value: 'usuarios', label: 'Usuarios' },
  { value: 'configuracion', label: 'Configuración' },
  { value: 'auditoria', label: 'Auditoría' },
]

const toolOptions: AccessOption[] = [
  { value: 'reportes', label: 'Reportes' },
  { value: 'exportaciones', label: 'Exportaciones' },
  { value: 'calculadora_margen', label: 'Calculadora de margen' },
  { value: 'proyecciones_financieras', label: 'Proyecciones financieras' },
  { value: 'simulador_iva', label: 'Simulador de IVA' },
  { value: 'simulador_descuentos', label: 'Simulador de descuentos' },
  { value: 'costeo_cotizaciones', label: 'Costeo de cotizaciones' },
  { value: 'control_caja_chica', label: 'Control de caja chica' },
  { value: 'calculo_horas_tecnicas', label: 'Cálculo de horas técnicas' },
  { value: 'scanner_qr', label: 'Escáner QR de seguimiento' },
]

const createFormDefaults = () => ({
  username: '',
  email: '',
  password: '',
  rol: 'ejecutivo' as RolEnum,
  nombre_completo: '',
  mfa_habilitado: false,
  force_mfa: false,
  permisos: [] as string[],
  vistas: [] as string[],
  herramientas: [] as string[],
})

const createForm = ref(createFormDefaults())

const editForm = ref({
  email: '',
  nombre_completo: '',
  rol: 'ejecutivo' as RolEnum,
  activo: true,
  mfa_habilitado: false,
  force_mfa: false,
  permisos: [] as string[],
  vistas: [] as string[],
  herramientas: [] as string[],
})

const columns = [
  { key: 'id_usuario', label: 'ID', class: 'w-16' },
  { key: 'username', label: 'Usuario' },
  { key: 'nombre_completo', label: 'Nombre Completo' },
  { key: 'email', label: 'Email' },
  { key: 'rol', label: 'Rol', class: 'w-40' },
  { key: 'activo', label: 'Estado', class: 'w-24' },
  { key: 'acciones', label: '', class: 'w-20' },
]

const filteredRows = computed(() =>
  usuarioStore.usuarios
    .filter((u) => {
      if (!searchQuery.value) return true
      const q = searchQuery.value.toLowerCase()
      return (
        u.username.toLowerCase().includes(q) ||
        (u.nombre_completo ?? '').toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q)
      )
    })
    .map((u) => ({ ...u, id: u.id_usuario }))
)

onMounted(() => usuarioStore.fetchUsuarios())

function openEdit(row: Record<string, unknown>): void {
  const user = usuarioStore.usuarios.find((u) => u.id_usuario === row.id_usuario)
  if (user) {
    selectedUser.value = user
    editForm.value = {
      email: user.email,
      nombre_completo: user.nombre_completo ?? '',
      rol: user.rol,
      activo: user.activo,
      mfa_habilitado: user.mfa_habilitado,
      force_mfa: user.force_mfa,
      permisos: [...user.permisos],
      vistas: [...user.vistas],
      herramientas: [...user.herramientas],
    }
    showEditModal.value = true
  }
}

async function handleCreate(): Promise<void> {
  saving.value = true
  formError.value = null
  try {
    await usuarioStore.createUsuario({
      username: createForm.value.username,
      email: createForm.value.email,
      password: createForm.value.password,
      rol: createForm.value.rol,
      nombre_completo: createForm.value.nombre_completo || undefined,
      mfa_habilitado: createForm.value.mfa_habilitado,
      force_mfa: createForm.value.force_mfa,
      permisos: createForm.value.permisos,
      vistas: createForm.value.vistas,
      herramientas: createForm.value.herramientas,
    })
    showCreateModal.value = false
    resetCreateForm()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al crear usuario'
  } finally {
    saving.value = false
  }
}

async function handleEdit(): Promise<void> {
  if (!selectedUser.value) return
  saving.value = true
  formError.value = null
  try {
    await usuarioStore.updateUsuario(selectedUser.value.id_usuario, {
      email: editForm.value.email,
      nombre_completo: editForm.value.nombre_completo || undefined,
      rol: editForm.value.rol,
      activo: editForm.value.activo,
      mfa_habilitado: editForm.value.mfa_habilitado,
      force_mfa: editForm.value.force_mfa,
      permisos: editForm.value.permisos,
      vistas: editForm.value.vistas,
      herramientas: editForm.value.herramientas,
    })
    showEditModal.value = false
    selectedUser.value = null
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al actualizar usuario'
  } finally {
    saving.value = false
  }
}

function resetCreateForm(): void {
  createForm.value = createFormDefaults()
  formError.value = null
}

function confirmDelete(row: Record<string, unknown>): void {
  const user = usuarioStore.usuarios.find((u) => u.id_usuario === row.id_usuario)
  if (!user) return
  selectedUser.value = user
  formError.value = null
  showDeleteModal.value = true
}

async function handleDelete(): Promise<void> {
  if (!selectedUser.value) return
  deleting.value = true
  formError.value = null
  try {
    await usuarioStore.deleteUsuario(selectedUser.value.id_usuario)
    showDeleteModal.value = false
    showEditModal.value = false
    selectedUser.value = null
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al eliminar usuario'
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="p-2 bg-blue-600 rounded-xl">
          <UserCog class="text-white" :size="22" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Gestión de Usuarios</h1>
          <p class="text-gray-500 text-sm mt-1">Administración de cuentas y roles del sistema (permisos, vistas y herramientas por casillas)</p>
        </div>
      </div>
      <Button @click="showCreateModal = true">
        <Plus :size="16" class="mr-2" />
        Nuevo Usuario
      </Button>
    </div>

    <Card :padding="false">
      <!-- Search -->
      <div class="p-4 border-b border-gray-100">
        <div class="relative max-w-sm">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="15" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Buscar por usuario, nombre o email..."
            class="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
      </div>

      <Table
        :columns="columns"
        :rows="filteredRows"
        :loading="usuarioStore.loading"
        @row-click="openEdit"
      >
        <template #rol="{ value }">
          <Badge :variant="value === 'superadmin' ? 'danger' : value === 'ejecutivo' ? 'warning' : 'info'">
            <ShieldCheck v-if="value === 'superadmin'" :size="11" class="mr-1" />
            {{ roleLabels[value as RolEnum] ?? value }}
          </Badge>
        </template>
        <template #activo="{ value }">
          <Badge :variant="value ? 'success' : 'default'">
            {{ value ? 'Activo' : 'Inactivo' }}
          </Badge>
        </template>
        <template #nombre_completo="{ value }">
          <span class="text-gray-600">{{ value || '—' }}</span>
        </template>
        <template #acciones="{ row }">
          <button
            @click.stop="confirmDelete(row as Record<string, unknown>)"
            class="p-2 text-red-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title="Eliminar usuario"
          >
            <Trash2 :size="14" />
          </button>
        </template>
      </Table>
    </Card>

    <!-- Create User Modal -->
    <Modal
      :open="showCreateModal"
      title="Nuevo Usuario"
      size="md"
      @close="showCreateModal = false; resetCreateForm()"
    >
      <form @submit.prevent="handleCreate" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Nombre de usuario *</label>
            <input
              v-model="createForm.username"
              required
              type="text"
              autocomplete="off"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Nombre Completo</label>
            <input
              v-model="createForm.nombre_completo"
              type="text"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              v-model="createForm.email"
              required
              type="email"
              autocomplete="off"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Contraseña *</label>
            <input
              v-model="createForm.password"
              required
              type="password"
              minlength="8"
              autocomplete="new-password"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
            <p class="text-xs text-gray-400 mt-1">Mínimo 8 caracteres</p>
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Rol *</label>
            <select
              v-model="createForm.rol"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white"
            >
              <option v-for="rol in roles" :key="rol" :value="rol">{{ roleLabels[rol] }}</option>
            </select>
          </div>
          <div>
            <label class="flex items-center gap-2 text-sm font-medium text-gray-700">
              <input v-model="createForm.mfa_habilitado" type="checkbox" class="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
              MFA habilitado
            </label>
          </div>
          <div>
            <label class="flex items-center gap-2 text-sm font-medium text-gray-700">
              <input v-model="createForm.force_mfa" type="checkbox" class="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
              MFA obligatorio
            </label>
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Permisos</label>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 border rounded-lg p-3 bg-gray-50">
              <label v-for="option in permissionOptions" :key="`create-perm-${option.value}`" class="flex items-center gap-2 text-sm text-gray-700">
                <input v-model="createForm.permisos" :value="option.value" type="checkbox" class="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                {{ option.label }}
              </label>
            </div>
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Vistas</label>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 border rounded-lg p-3 bg-gray-50">
              <label v-for="option in viewOptions" :key="`create-view-${option.value}`" class="flex items-center gap-2 text-sm text-gray-700">
                <input v-model="createForm.vistas" :value="option.value" type="checkbox" class="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                {{ option.label }}
              </label>
            </div>
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Herramientas</label>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 border rounded-lg p-3 bg-gray-50">
              <label v-for="option in toolOptions" :key="`create-tool-${option.value}`" class="flex items-center gap-2 text-sm text-gray-700">
                <input v-model="createForm.herramientas" :value="option.value" type="checkbox" class="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                {{ option.label }}
              </label>
            </div>
          </div>
        </div>

        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>

        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" @click="showCreateModal = false; resetCreateForm()">
            Cancelar
          </Button>
          <Button type="submit" :loading="saving">Crear Usuario</Button>
        </div>
      </form>
    </Modal>

    <!-- Edit User Modal -->
    <Modal
      :open="showEditModal"
      :title="`Editar: ${selectedUser?.username}`"
      size="md"
      @close="showEditModal = false; selectedUser = null; formError = null"
    >
      <form v-if="selectedUser" @submit.prevent="handleEdit" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Nombre Completo</label>
            <input
              v-model="editForm.nombre_completo"
              type="text"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              v-model="editForm.email"
              required
              type="email"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Rol *</label>
            <select
              v-model="editForm.rol"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white"
            >
              <option v-for="rol in roles" :key="rol" :value="rol">{{ roleLabels[rol] }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Estado</label>
            <select
              v-model="editForm.activo"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white"
            >
              <option :value="true">Activo</option>
              <option :value="false">Inactivo</option>
            </select>
          </div>
          <div>
            <label class="flex items-center gap-2 text-sm font-medium text-gray-700">
              <input v-model="editForm.mfa_habilitado" type="checkbox" class="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
              MFA habilitado
            </label>
          </div>
          <div>
            <label class="flex items-center gap-2 text-sm font-medium text-gray-700">
              <input v-model="editForm.force_mfa" type="checkbox" class="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
              MFA obligatorio
            </label>
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Permisos</label>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 border rounded-lg p-3 bg-gray-50">
              <label v-for="option in permissionOptions" :key="`edit-perm-${option.value}`" class="flex items-center gap-2 text-sm text-gray-700">
                <input v-model="editForm.permisos" :value="option.value" type="checkbox" class="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                {{ option.label }}
              </label>
            </div>
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Vistas</label>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 border rounded-lg p-3 bg-gray-50">
              <label v-for="option in viewOptions" :key="`edit-view-${option.value}`" class="flex items-center gap-2 text-sm text-gray-700">
                <input v-model="editForm.vistas" :value="option.value" type="checkbox" class="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                {{ option.label }}
              </label>
            </div>
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Herramientas</label>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 border rounded-lg p-3 bg-gray-50">
              <label v-for="option in toolOptions" :key="`edit-tool-${option.value}`" class="flex items-center gap-2 text-sm text-gray-700">
                <input v-model="editForm.herramientas" :value="option.value" type="checkbox" class="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                {{ option.label }}
              </label>
            </div>
          </div>
        </div>

        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>

        <div class="flex justify-end gap-3 pt-2">
          <Button
            variant="secondary"
            type="button"
            class="mr-auto"
            @click="showDeleteModal = true"
          >
            <Trash2 :size="14" class="mr-2" />
            Eliminar
          </Button>
          <Button
            variant="secondary"
            type="button"
            @click="showEditModal = false; selectedUser = null; formError = null"
          >
            Cancelar
          </Button>
          <Button type="submit" :loading="saving">Guardar Cambios</Button>
        </div>
      </form>
    </Modal>

    <Modal
      :open="showDeleteModal"
      title="Eliminar Usuario"
      size="sm"
      @close="showDeleteModal = false; formError = null"
    >
      <div class="space-y-4">
        <p class="text-sm text-gray-600">
          Esta acción eliminará la cuenta <strong>{{ selectedUser?.username }}</strong>. Úsala solo cuando ya no deba existir en el sistema.
        </p>
        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>
        <div class="flex justify-end gap-3">
          <Button variant="secondary" type="button" @click="showDeleteModal = false">Cancelar</Button>
          <Button :loading="deleting" @click="handleDelete">Eliminar Usuario</Button>
        </div>
      </div>
    </Modal>
  </div>
</template>

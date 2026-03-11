<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Building2, User } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import { useClienteStore } from '../stores/clientes'

const clienteStore = useClienteStore()
const router = useRouter()

const searchQuery = ref('')
const filterTipo = ref<'all' | 'B2B' | 'B2C'>('all')
const showCreateModal = ref(false)

// Form
const form = ref({
  tipo_cliente: 'B2B' as 'B2B' | 'B2C',
  estado: 'activo' as const,
  empresa: {
    razon_social: '',
    ruc: '',
    contacto_principal: '',
    telefono: '',
    email: '',
  },
  cliente_b2c: {
    nombre_completo: '',
    documento_identidad: '',
    telefono: '',
    email: '',
  },
})
const saving = ref(false)
const formError = ref<string | null>(null)

const columns = [
  { key: 'id_cliente', label: 'ID', class: 'w-16' },
  { key: 'tipo', label: 'Tipo', class: 'w-24' },
  { key: 'nombre', label: 'Nombre / Razón Social' },
  { key: 'contacto', label: 'Contacto' },
  { key: 'estado', label: 'Estado', class: 'w-28' },
  { key: 'fecha_registro', label: 'Registro', class: 'w-32' },
]

const tableRows = computed(() =>
  clienteStore.clientes
    .filter((c) => {
      if (filterTipo.value !== 'all' && c.tipo_cliente !== filterTipo.value) return false
      if (!searchQuery.value) return true
      const q = searchQuery.value.toLowerCase()
      const nombre =
        c.empresa?.razon_social ?? c.cliente_b2c?.nombre_completo ?? ''
      const ruc = c.empresa?.ruc ?? c.cliente_b2c?.documento_identidad ?? ''
      return nombre.toLowerCase().includes(q) || ruc.toLowerCase().includes(q)
    })
    .map((c) => ({
      ...c,
      id: c.id_cliente,
      tipo: c.tipo_cliente,
      nombre: c.empresa?.razon_social ?? c.cliente_b2c?.nombre_completo ?? '—',
      contacto: c.empresa?.email ?? c.cliente_b2c?.email ?? '—',
    }))
)

onMounted(() => clienteStore.fetchClientes())

function goToDetail(row: Record<string, unknown>): void {
  router.push(`/crm/${row.id_cliente}`)
}

async function handleCreate(): Promise<void> {
  saving.value = true
  formError.value = null
  try {
    const payload =
      form.value.tipo_cliente === 'B2B'
        ? { tipo_cliente: 'B2B', estado: form.value.estado, empresa: form.value.empresa }
        : { tipo_cliente: 'B2C', estado: form.value.estado, cliente_b2c: form.value.cliente_b2c }
    await clienteStore.createCliente(payload)
    showCreateModal.value = false
    resetForm()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al crear cliente'
  } finally {
    saving.value = false
  }
}

function resetForm(): void {
  form.value = {
    tipo_cliente: 'B2B',
    estado: 'activo',
    empresa: { razon_social: '', ruc: '', contacto_principal: '', telefono: '', email: '' },
    cliente_b2c: { nombre_completo: '', documento_identidad: '', telefono: '', email: '' },
  }
  formError.value = null
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">CRM — Clientes</h1>
        <p class="text-gray-500 text-sm mt-1">Gestión de clientes B2B y B2C</p>
      </div>
      <Button @click="showCreateModal = true">
        <Plus :size="16" class="mr-2" />
        Nuevo Cliente
      </Button>
    </div>

    <Card :padding="false">
      <!-- Filters -->
      <div class="p-4 border-b border-gray-100 flex flex-wrap gap-3">
        <div class="relative flex-1 min-w-[200px]">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="15" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Buscar por nombre o RUC..."
            class="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
        <div class="flex gap-2">
          <button
            v-for="opt in [{ val: 'all', label: 'Todos' }, { val: 'B2B', label: 'B2B' }, { val: 'B2C', label: 'B2C' }]"
            :key="opt.val"
            @click="filterTipo = opt.val as typeof filterTipo"
            :class="[
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              filterTipo === opt.val
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
            ]"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <Table
        :columns="columns"
        :rows="tableRows"
        :loading="clienteStore.loading"
        @row-click="goToDetail"
      >
        <template #tipo="{ value }">
          <Badge :variant="value === 'B2B' ? 'b2b' : 'b2c'">
            <component :is="value === 'B2B' ? Building2 : User" :size="11" class="mr-1" />
            {{ value }}
          </Badge>
        </template>
        <template #estado="{ value }">
          <Badge
            :variant="value === 'activo' ? 'success' : value === 'prospecto' ? 'warning' : 'default'"
          >{{ value }}</Badge>
        </template>
        <template #fecha_registro="{ value }">
          <span class="text-xs text-gray-500">{{ value }}</span>
        </template>
      </Table>
    </Card>

    <!-- Create Modal -->
    <Modal :open="showCreateModal" title="Nuevo Cliente" size="lg" @close="showCreateModal = false; resetForm()">
      <form @submit.prevent="handleCreate" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Tipo de Cliente</label>
          <div class="flex gap-3">
            <label class="flex items-center gap-2 cursor-pointer">
              <input v-model="form.tipo_cliente" type="radio" value="B2B" class="text-blue-600" />
              <span class="flex items-center gap-1 text-sm"><Building2 :size="15" /> Empresa (B2B)</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input v-model="form.tipo_cliente" type="radio" value="B2C" class="text-blue-600" />
              <span class="flex items-center gap-1 text-sm"><User :size="15" /> Persona (B2C)</span>
            </label>
          </div>
        </div>

        <!-- B2B fields -->
        <template v-if="form.tipo_cliente === 'B2B'">
          <div class="grid grid-cols-2 gap-4">
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Razón Social *</label>
              <input v-model="form.empresa.razon_social" required type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">RUC *</label>
              <input v-model="form.empresa.ruc" required type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Contacto Principal</label>
              <input v-model="form.empresa.contacto_principal" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
              <input v-model="form.empresa.telefono" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input v-model="form.empresa.email" type="email" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
            </div>
          </div>
        </template>

        <!-- B2C fields -->
        <template v-else>
          <div class="grid grid-cols-2 gap-4">
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Nombre Completo *</label>
              <input v-model="form.cliente_b2c.nombre_completo" required type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">DNI / Documento *</label>
              <input v-model="form.cliente_b2c.documento_identidad" required type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
              <input v-model="form.cliente_b2c.telefono" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
            </div>
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input v-model="form.cliente_b2c.email" type="email" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
            </div>
          </div>
        </template>

        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>

        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" @click="showCreateModal = false; resetForm()">Cancelar</Button>
          <Button type="submit" :loading="saving">Crear Cliente</Button>
        </div>
      </form>
    </Modal>
  </div>
</template>

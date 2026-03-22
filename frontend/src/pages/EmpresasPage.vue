<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { Building2, Pencil, Plus, Trash2 } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import { useI18n } from 'vue-i18n'
import { useClienteStore } from '../stores/clientes'
import { useAuthStore } from '../stores/auth'
import type { EstadoCliente } from '../types'

const clienteStore = useClienteStore()
const auth = useAuthStore()

const loading = ref(true)
const showCreateModal = ref(false)
const saving = ref(false)
const formError = ref<string | null>(null)
const deletingCompanyId = ref<number | null>(null)
const editingCompanyId = ref<number | null>(null)
const { t } = useI18n()

const form = ref<{
  razon_social: string
  ruc: string
  contacto_principal: string
  telefono: string
  email: string
  direccion: string
  sector: string
  estado: EstadoCliente
}>({
  razon_social: '',
  ruc: '',
  contacto_principal: '',
  telefono: '',
  email: '',
  direccion: '',
  sector: '',
  estado: 'activo',
})

const columns = [
  { key: 'razon_social', label: t('companyPage.companyName') },
  { key: 'ruc', label: 'RUC' },
  { key: 'contacto_principal', label: t('companyPage.contact') },
  { key: 'telefono', label: t('companyPage.phone') },
  { key: 'estado', label: t('companyPage.status') },
  { key: 'acciones', label: t('common.actions'), class: 'w-40' },
]

const empresas = computed(() =>
  clienteStore.clientes
    .filter((item) => item.tipo_cliente === 'B2B' && item.empresa)
    .map((item) => ({
      id: item.id_cliente,
      id_cliente: item.id_cliente,
      razon_social: item.empresa?.razon_social ?? '',
      ruc: item.empresa?.ruc ?? '',
      contacto_principal: item.empresa?.contacto_principal ?? '—',
      telefono: item.empresa?.telefono ?? '—',
      email: item.empresa?.email ?? '',
      direccion: item.empresa?.direccion ?? '',
      sector: item.empresa?.sector ?? '',
      estado: item.estado,
    }))
)

const canManage = computed(() => {
  const permisos = auth.user?.permisos ?? []
  return permisos.includes('*') || permisos.includes('empresas.manage') || permisos.includes('clientes.manage')
})
const canDelete = computed(() => auth.user?.rol === 'superadmin')

function resetForm(): void {
  form.value = {
    razon_social: '',
    ruc: '',
    contacto_principal: '',
    telefono: '',
    email: '',
    direccion: '',
    sector: '',
    estado: 'activo',
  }
  editingCompanyId.value = null
  formError.value = null
}

async function loadData(): Promise<void> {
  loading.value = true
  formError.value = null
  try {
    await clienteStore.fetchClientes('B2B')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } }; message?: string }
    formError.value = err.response?.data?.detail ?? err.message ?? t('companyPage.loadError')
  } finally {
    loading.value = false
  }
}

function openCreateModal(): void {
  resetForm()
  showCreateModal.value = true
}

function openEditModal(row: {
  id_cliente: number
  razon_social: string
  ruc: string
  contacto_principal: string
  telefono: string
  email: string
  direccion: string
  sector: string
  estado: EstadoCliente
}): void {
  editingCompanyId.value = row.id_cliente
  form.value = {
    razon_social: row.razon_social,
    ruc: row.ruc,
    contacto_principal: row.contacto_principal === '—' ? '' : row.contacto_principal,
    telefono: row.telefono === '—' ? '' : row.telefono,
    email: row.email,
    direccion: row.direccion,
    sector: row.sector,
    estado: row.estado,
  }
  showCreateModal.value = true
}

async function saveCompany(): Promise<void> {
  if (!canManage.value) {
    formError.value = t('companyPage.permissionError')
    return
  }

  if (!form.value.razon_social.trim() || !form.value.ruc.trim()) {
    formError.value = t('companyPage.requiredFields')
    return
  }

  saving.value = true
  formError.value = null
  try {
    const payload = {
      estado: form.value.estado,
      empresa: {
        razon_social: form.value.razon_social.trim(),
        ruc: form.value.ruc.trim(),
        contacto_principal: form.value.contacto_principal || undefined,
        telefono: form.value.telefono || undefined,
        email: form.value.email || undefined,
        direccion: form.value.direccion || undefined,
        sector: form.value.sector || undefined,
      },
    }

    if (editingCompanyId.value) {
      await clienteStore.updateCliente(editingCompanyId.value, payload)
    } else {
      await clienteStore.createCliente({
        tipo_cliente: 'B2B',
        ...payload,
      })
    }

    showCreateModal.value = false
    resetForm()
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } }; message?: string }
    formError.value = err.response?.data?.detail ?? err.message ?? t('companyPage.saveError')
  } finally {
    saving.value = false
  }
}

async function deleteCompany(idCliente: number): Promise<void> {
  if (!canDelete.value) {
    formError.value = t('companyPage.deletePermissionError')
    return
  }

  const confirmed = window.confirm(t('companyPage.confirmDelete'))
  if (!confirmed) return

  deletingCompanyId.value = idCliente
  formError.value = null
  try {
    await clienteStore.deleteCliente(idCliente)
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } }; message?: string }
    formError.value = err.response?.data?.detail ?? err.message ?? t('companyPage.deleteError')
  } finally {
    deletingCompanyId.value = null
  }
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3">
      <div class="p-2 bg-gray-800 rounded-xl">
        <Building2 class="text-white" :size="22" />
      </div>
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">{{ t('empresas.title') }}</h1>
        <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">{{ t('companyPage.subtitle') }}</p>
      </div>
    </div>

    <div class="flex justify-end">
      <Button :disabled="!canManage" @click="openCreateModal">
        <Plus :size="14" class="mr-2" />
        {{ t('companyPage.newCompany') }}
      </Button>
    </div>

    <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>

    <Card :padding="false">
      <div v-if="!loading && empresas.length === 0" class="text-center py-10 text-sm text-gray-500">
        {{ t('companyPage.emptyState') }}
      </div>
      <Table v-else :columns="columns" :rows="empresas" :loading="loading">
        <template #estado="{ value }">
          <span
            :class="[
              'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
              value === 'activo' ? 'bg-green-100 text-green-700' : value === 'inactivo' ? 'bg-slate-100 text-slate-600' : 'bg-amber-100 text-amber-700'
            ]"
          >
            {{ value }}
          </span>
        </template>
        <template #acciones="{ row }">
          <div class="flex items-center gap-2">
            <button
              :disabled="!canManage"
              @click.stop="openEditModal(row as never)"
              class="px-2 py-1 text-xs bg-slate-900 text-white rounded-lg hover:bg-slate-800 disabled:opacity-60 inline-flex items-center gap-1"
            >
              <Pencil :size="12" />
              {{ t('common.edit') }}
            </button>
            <button
              :disabled="!canDelete || deletingCompanyId === Number((row as Record<string, unknown>).id_cliente)"
              @click.stop="deleteCompany(Number((row as Record<string, unknown>).id_cliente))"
              class="px-2 py-1 text-xs bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-60 inline-flex items-center gap-1"
            >
              <Trash2 :size="12" />
              {{ t('common.delete') }}
            </button>
          </div>
        </template>
      </Table>
    </Card>

    <Modal :open="showCreateModal" :title="editingCompanyId ? t('companyPage.editCompany') : t('companyPage.newCompany')" size="md" @close="showCreateModal = false; resetForm()">
      <form class="space-y-3" @submit.prevent="saveCompany">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('companyPage.companyName') }} *</label>
          <input v-model="form.razon_social" type="text" required class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">RUC *</label>
          <input v-model="form.ruc" type="text" required class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('companyPage.contact') }}</label>
            <input v-model="form.contacto_principal" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('companyPage.phone') }}</label>
            <input v-model="form.telefono" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
            <input v-model="form.email" type="email" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('companyPage.address') }}</label>
            <input v-model="form.direccion" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('companyPage.sector') }}</label>
            <input v-model="form.sector" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('companyPage.status') }}</label>
            <select v-model="form.estado" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white">
              <option value="activo">Activo</option>
              <option value="inactivo">Inactivo</option>
              <option value="prospecto">Prospecto</option>
            </select>
          </div>
        </div>
        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" @click="showCreateModal = false; resetForm()">{{ t('common.cancel') }}</Button>
          <Button type="submit" :loading="saving">{{ t('common.save') }}</Button>
        </div>
      </form>
    </Modal>
  </div>
</template>

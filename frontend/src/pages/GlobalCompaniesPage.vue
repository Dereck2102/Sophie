<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import api from '../services/api'
import type { GlobalCompany, GlobalCompanyUpdate } from '../types'

const loading = ref(false)
const saving = ref(false)
const mutating = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)
const companies = ref<GlobalCompany[]>([])
const editModalOpen = ref(false)
const editingCompanyId = ref<number | null>(null)
const form = ref<GlobalCompanyUpdate>({ nombre: '', ruc: '' })

const sortedCompanies = computed(() => [...companies.value].sort((a, b) => a.nombre.localeCompare(b.nombre)))

async function loadCompanies(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get<GlobalCompany[]>('/api/v1/global/companies', { params: { limit: 500 } })
    companies.value = data
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo cargar empresas globales'
  } finally {
    loading.value = false
  }
}

function openEdit(company: GlobalCompany): void {
  editingCompanyId.value = company.id_empresa
  form.value = { nombre: company.nombre, ruc: company.ruc }
  editModalOpen.value = true
}

async function saveEdit(): Promise<void> {
  if (!editingCompanyId.value) return
  saving.value = true
  error.value = null
  success.value = null
  try {
    await api.patch(`/api/v1/global/companies/${editingCompanyId.value}`, form.value)
    success.value = 'Empresa actualizada'
    editModalOpen.value = false
    await loadCompanies()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo actualizar la empresa'
  } finally {
    saving.value = false
  }
}

async function toggleSuspend(company: GlobalCompany): Promise<void> {
  mutating.value = true
  error.value = null
  success.value = null
  try {
    if (company.estado === 'activo') {
      await api.post(`/api/v1/global/companies/${company.id_empresa}/suspend`)
      success.value = `Empresa ${company.nombre} suspendida`
    } else {
      await api.post(`/api/v1/global/companies/${company.id_empresa}/activate`)
      success.value = `Empresa ${company.nombre} activada`
    }
    await loadCompanies()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo cambiar el estado de la empresa'
  } finally {
    mutating.value = false
  }
}

async function deleteCompany(company: GlobalCompany): Promise<void> {
  if (!window.confirm(`¿Eliminar empresa ${company.nombre}? Esta acción es irreversible.`)) return
  mutating.value = true
  error.value = null
  success.value = null
  try {
    await api.delete(`/api/v1/global/companies/${company.id_empresa}`)
    success.value = `Empresa ${company.nombre} eliminada`
    await loadCompanies()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo eliminar la empresa'
  } finally {
    mutating.value = false
  }
}

onMounted(() => {
  void loadCompanies()
})
</script>

<template>
  <div class="space-y-6">
    <section class="rounded-2xl border border-gray-200 bg-white p-5">
      <h2 class="text-xl font-bold text-gray-900">Gestión Global de Empresas</h2>
      <p class="text-sm text-gray-600 mt-1">Editar datos básicos, activar/suspender y eliminar empresas.</p>
    </section>

    <p v-if="error" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
    <p v-if="success" class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{{ success }}</p>

    <Card title="Empresas registradas" subtitle="SOPHIE ADMIN · Superadmin">
      <div v-if="loading" class="text-sm text-gray-500">Cargando empresas...</div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left border-b border-gray-200">
              <th class="px-2 py-2">Empresa</th>
              <th class="px-2 py-2">RUC</th>
              <th class="px-2 py-2">Plan</th>
              <th class="px-2 py-2">Estado</th>
              <th class="px-2 py-2">Módulos</th>
              <th class="px-2 py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in sortedCompanies" :key="item.id_empresa" class="border-b border-gray-100">
              <td class="px-2 py-2 font-medium">{{ item.nombre }}</td>
              <td class="px-2 py-2">{{ item.ruc }}</td>
              <td class="px-2 py-2 uppercase">{{ item.plan_tier }}</td>
              <td class="px-2 py-2">
                <span :class="item.estado === 'activo' ? 'text-emerald-700' : 'text-amber-700'">{{ item.estado }}</span>
              </td>
              <td class="px-2 py-2">{{ item.modules_enabled.length }}</td>
              <td class="px-2 py-2">
                <div class="flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" :disabled="mutating" @click="openEdit(item)">Editar</Button>
                  <Button
                    size="sm"
                    :variant="item.estado === 'activo' ? 'danger' : 'secondary'"
                    :disabled="mutating"
                    @click="toggleSuspend(item)"
                  >
                    {{ item.estado === 'activo' ? 'Suspender' : 'Activar' }}
                  </Button>
                  <Button size="sm" variant="danger" :disabled="mutating" @click="deleteCompany(item)">Eliminar</Button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>

    <Modal :open="editModalOpen" title="Editar Empresa" size="sm" @close="editModalOpen = false">
      <form class="space-y-3" @submit.prevent="saveEdit">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
          <input v-model="form.nombre" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" required />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">RUC</label>
          <input v-model="form.ruc" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" required />
        </div>
        <div class="flex justify-end gap-2">
          <Button type="button" variant="secondary" @click="editModalOpen = false">Cancelar</Button>
          <Button type="submit" :loading="saving">Guardar</Button>
        </div>
      </form>
    </Modal>
  </div>
</template>

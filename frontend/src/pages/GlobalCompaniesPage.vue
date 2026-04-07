<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Building2, Grid3X3, LayoutList, List, Search, Eye, EyeOff, Pencil, Trash2, ArrowRight } from 'lucide-vue-next'
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
const router = useRouter()
const searchQuery = ref('')
const statusFilter = ref<'all' | 'activo' | 'inactivo' | 'prospecto'>('all')
const planFilter = ref<'all' | string>('all')
const viewMode = ref<'lista' | 'recuadro' | 'simple' | 'completa'>('lista')

const form = ref<GlobalCompanyUpdate>({ nombre: '', branding_nombre: '', branding_logo_url: '', ruc: '' })

function isValidRuc(value: string): boolean {
  return /^\d{10,13}$/.test(value.trim())
}

const sortedCompanies = computed(() => [...companies.value].sort((a, b) => a.nombre.localeCompare(b.nombre)))
const availablePlans = computed(() => {
  const plans = new Set<string>()
  for (const company of companies.value) {
    plans.add(company.plan_tier)
  }
  return Array.from(plans).sort()
})

const filteredCompanies = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  return sortedCompanies.value.filter((item) => {
    const matchesQuery = !query
      || item.nombre.toLowerCase().includes(query)
      || (item.branding_nombre ?? '').toLowerCase().includes(query)
      || item.ruc.toLowerCase().includes(query)
    const matchesStatus = statusFilter.value === 'all' || item.estado === statusFilter.value
    const matchesPlan = planFilter.value === 'all' || item.plan_tier === planFilter.value
    return matchesQuery && matchesStatus && matchesPlan
  })
})

function statusClass(status: GlobalCompany['estado']): string {
  if (status === 'activo') return 'text-emerald-700'
  if (status === 'inactivo') return 'text-amber-700'
  return 'text-slate-600'
}

function openEdit(company: GlobalCompany): void {
  editingCompanyId.value = company.id_empresa
  form.value = {
    nombre: company.nombre,
    branding_nombre: company.branding_nombre ?? '',
    branding_logo_url: company.branding_logo_url ?? '',
    ruc: company.ruc,
  }
  editModalOpen.value = true
}

function goToCompany(companyId: number): void {
  void router.push({ name: 'GlobalCompanyDetail', params: { companyId: String(companyId) } })
}

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

async function saveEdit(): Promise<void> {
  if (!editingCompanyId.value) return
  const normalizedRuc = (form.value.ruc ?? '').trim()
  if (!isValidRuc(normalizedRuc)) {
    error.value = 'RUC inválido. Debe contener entre 10 y 13 dígitos.'
    return
  }

  saving.value = true
  error.value = null
  success.value = null
  try {
    await api.patch(`/api/v1/global/companies/${editingCompanyId.value}`, {
      ...form.value,
      ruc: normalizedRuc,
    })
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
      <p class="text-sm text-gray-600 mt-1">Haz click en una empresa para ir a su pantalla completa de gestión.</p>
    </section>

    <p v-if="error" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
    <p v-if="success" class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{{ success }}</p>

    <Card title="Empresas registradas" subtitle="SOPHIE ADMIN · Superadmin">
      <div class="mb-4 grid grid-cols-1 md:grid-cols-4 gap-3">
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Buscar</label>
          <div class="relative">
            <Search :size="16" class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              v-model="searchQuery"
              type="text"
              class="w-full rounded-lg border pl-9 pr-3 py-2 text-sm"
              placeholder="Empresa, branding o RUC"
            />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Estado</label>
          <select v-model="statusFilter" class="w-full rounded-lg border px-3 py-2 text-sm">
            <option value="all">Todos</option>
            <option value="activo">Activo</option>
            <option value="inactivo">Inactivo</option>
            <option value="prospecto">Prospecto</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Plan</label>
          <select v-model="planFilter" class="w-full rounded-lg border px-3 py-2 text-sm">
            <option value="all">Todos</option>
            <option v-for="plan in availablePlans" :key="plan" :value="plan">{{ plan.toUpperCase() }}</option>
          </select>
        </div>
      </div>

      <div class="mb-4 flex flex-wrap gap-2">
        <Button size="sm" :variant="viewMode === 'lista' ? 'primary' : 'secondary'" @click="viewMode = 'lista'">
          <LayoutList :size="14" class="mr-1" /> Lista
        </Button>
        <Button size="sm" :variant="viewMode === 'recuadro' ? 'primary' : 'secondary'" @click="viewMode = 'recuadro'">
          <Grid3X3 :size="14" class="mr-1" /> Recuadro
        </Button>
        <Button size="sm" :variant="viewMode === 'simple' ? 'primary' : 'secondary'" @click="viewMode = 'simple'">
          <List :size="14" class="mr-1" /> Vista simple
        </Button>
        <Button size="sm" :variant="viewMode === 'completa' ? 'primary' : 'secondary'" @click="viewMode = 'completa'">
          <Building2 :size="14" class="mr-1" /> Vista completa
        </Button>
      </div>

      <div v-if="loading" class="text-sm text-gray-500">Cargando empresas...</div>
      <div v-else-if="filteredCompanies.length === 0" class="text-sm text-gray-500">No hay resultados con los filtros actuales.</div>

      <div v-else-if="viewMode === 'lista'" class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left border-b border-gray-200">
              <th class="px-2 py-2">Empresa</th>
              <th class="px-2 py-2">Branding ERP</th>
              <th class="px-2 py-2">Plan</th>
              <th class="px-2 py-2">Estado</th>
              <th class="px-2 py-2">Acciones rápidas</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in filteredCompanies"
              :key="item.id_empresa"
              class="border-b border-gray-100 cursor-pointer"
              @click="goToCompany(item.id_empresa)"
            >
              <td class="px-2 py-2 font-medium">{{ item.nombre }}</td>
              <td class="px-2 py-2">{{ item.branding_nombre ?? item.nombre }}</td>
              <td class="px-2 py-2 uppercase">{{ item.plan_tier }}</td>
              <td class="px-2 py-2">
                <span :class="statusClass(item.estado)">{{ item.estado }}</span>
              </td>
              <td class="px-2 py-2">
                <div class="flex flex-wrap gap-2" @click.stop>
                  <Button size="sm" variant="primary" @click="goToCompany(item.id_empresa)">
                    <ArrowRight :size="14" class="mr-1" /> Gestionar
                  </Button>
                  <Button size="sm" variant="secondary" :disabled="mutating" @click="openEdit(item)">
                    <Pencil :size="14" class="mr-1" /> Editar
                  </Button>
                  <Button
                    size="sm"
                    :variant="item.estado === 'activo' ? 'danger' : 'secondary'"
                    :disabled="mutating"
                    @click="toggleSuspend(item)"
                  >
                    <component :is="item.estado === 'activo' ? EyeOff : Eye" :size="14" class="mr-1" />
                    {{ item.estado === 'activo' ? 'Suspender' : 'Activar' }}
                  </Button>
                  <Button size="sm" variant="danger" :disabled="mutating" @click="deleteCompany(item)">
                    <Trash2 :size="14" class="mr-1" /> Eliminar
                  </Button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="viewMode === 'simple'" class="space-y-2">
        <button
          v-for="item in filteredCompanies"
          :key="`simple-${item.id_empresa}`"
          class="w-full border rounded-lg px-3 py-2 text-left hover:bg-gray-50 flex items-center justify-between"
          @click="goToCompany(item.id_empresa)"
        >
          <span class="font-medium text-sm">{{ item.nombre }}</span>
          <span class="text-xs" :class="statusClass(item.estado)">{{ item.estado }}</span>
        </button>
      </div>

      <div v-else-if="viewMode === 'recuadro'" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        <article
          v-for="item in filteredCompanies"
          :key="`card-${item.id_empresa}`"
          class="rounded-xl border p-4 hover:bg-gray-50 cursor-pointer"
          @click="goToCompany(item.id_empresa)"
        >
          <h3 class="font-semibold text-gray-900 truncate">{{ item.nombre }}</h3>
          <p class="text-sm text-gray-500 mt-1 truncate">{{ item.ruc }}</p>
          <div class="mt-3 flex items-center justify-between text-sm">
            <span class="uppercase">{{ item.plan_tier }}</span>
            <span :class="statusClass(item.estado)">{{ item.estado }}</span>
          </div>
        </article>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        <article
          v-for="item in filteredCompanies"
          :key="`full-${item.id_empresa}`"
          class="rounded-xl border p-4 hover:bg-gray-50 cursor-pointer"
          @click="goToCompany(item.id_empresa)"
        >
          <div class="flex items-center gap-3">
            <div class="h-12 w-12 rounded-lg border bg-gray-100 overflow-hidden flex items-center justify-center">
              <img
                v-if="item.branding_logo_url"
                :src="item.branding_logo_url"
                :alt="item.nombre"
                class="h-full w-full object-cover"
              />
              <Building2 v-else :size="20" class="text-gray-400" />
            </div>
            <div class="min-w-0">
              <h3 class="font-semibold text-gray-900 truncate">{{ item.nombre }}</h3>
              <p class="text-sm text-gray-500 truncate">{{ item.branding_nombre ?? 'Sin branding ERP' }}</p>
            </div>
          </div>
          <div class="mt-3 flex items-center justify-between text-sm">
            <span class="uppercase">{{ item.plan_tier }}</span>
            <span :class="statusClass(item.estado)">{{ item.estado }}</span>
          </div>
        </article>
      </div>
    </Card>

    <Modal :open="editModalOpen" title="Editar Empresa" size="md" @close="editModalOpen = false">
      <form class="space-y-3" @submit.prevent="saveEdit">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Nombre legal</label>
          <input v-model="form.nombre" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" required />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">RUC</label>
          <input v-model="form.ruc" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" required />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Branding ERP (nombre mostrado)</label>
          <input v-model="form.branding_nombre" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" placeholder="Opcional" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Logo ERP URL</label>
          <input v-model="form.branding_logo_url" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" placeholder="https://..." />
        </div>
        <div class="flex justify-end gap-2">
          <Button type="button" variant="secondary" @click="editModalOpen = false">Cancelar</Button>
          <Button type="submit" :loading="saving">Guardar</Button>
        </div>
      </form>
    </Modal>
  </div>
</template>

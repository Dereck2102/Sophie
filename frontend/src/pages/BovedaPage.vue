<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { Eye, Lock, Plus } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import api from '../services/api'
import { useBovedaStore } from '../stores/boveda'
import type { Cliente } from '../types'
import type { CredencialReveal } from '../types/boveda'

const bovedaStore = useBovedaStore()
const { credenciales, loading: bovedaLoading, error: bovedaError } = storeToRefs(bovedaStore)
const empresas = ref<Array<{ id_cliente: number; nombre: string }>>([])
const loading = ref(true)
const mfaRequired = ref(false)
const showCreateModal = ref(false)
const showRevealModal = ref(false)
const revealData = ref<CredencialReveal | null>(null)
const saving = ref(false)
const revealing = ref(false)
const formError = ref<string | null>(null)

const form = ref({
  id_empresa: 0,
  nombre: '',
  usuario_acceso: '',
  password_plain: '',
  url: '',
  notas: '',
})

const columns = [
  { key: 'id_empresa', label: 'Empresa' },
  { key: 'nombre', label: 'Nombre' },
  { key: 'usuario_acceso', label: 'Usuario' },
  { key: 'url', label: 'URL' },
  { key: 'acciones', label: 'Acciones', class: 'w-36' },
]

const empresasMap = computed<Record<number, string>>(() =>
  empresas.value.reduce<Record<number, string>>((acc, empresa) => {
    acc[empresa.id_cliente] = empresa.nombre
    return acc
  }, {})
)

function getEmpresaNombre(idEmpresa: number): string {
  return empresasMap.value[idEmpresa] ?? `Empresa #${idEmpresa}`
}

function resetForm(): void {
  form.value = {
    id_empresa: 0,
    nombre: '',
    usuario_acceso: '',
    password_plain: '',
    url: '',
    notas: '',
  }
  formError.value = null
}

async function loadData(): Promise<void> {
  loading.value = true
  formError.value = null
  mfaRequired.value = false
  try {
    const [bovedaResult, clientesResult] = await Promise.allSettled([
      bovedaStore.fetchCredenciales(),
      api.get<Cliente[]>('/api/v1/clientes/', { params: { limit: 200 } }),
    ])
    if (clientesResult.status === 'fulfilled') {
      empresas.value = clientesResult.value.data
        .filter((cliente) => !!cliente.empresa?.razon_social)
        .map((cliente) => ({
          id_cliente: cliente.id_cliente,
          nombre: cliente.empresa?.razon_social ?? `Empresa #${cliente.id_cliente}`,
        }))
    }

    if (bovedaResult.status === 'rejected') {
      const err = bovedaResult.reason as { response?: { status?: number; data?: { detail?: string } } }
      if (err.response?.status === 403) mfaRequired.value = true
      formError.value = err.response?.data?.detail ?? bovedaError.value ?? 'No se pudo cargar la bóveda'
    }

    if (clientesResult.status === 'rejected') {
      const err = clientesResult.reason as { response?: { status?: number; data?: { detail?: string } } }
      formError.value = formError.value ?? err.response?.data?.detail ?? 'No se pudo cargar el catálogo de empresas'
    }
  } catch (e: unknown) {
    const err = e as { response?: { status?: number; data?: { detail?: string } } }
    if (err.response?.status === 403) mfaRequired.value = true
    formError.value = err.response?.data?.detail ?? null
  } finally {
    loading.value = false
  }
}

async function handleCreate(): Promise<void> {
  if (!form.value.id_empresa || !form.value.nombre || !form.value.password_plain) {
    formError.value = 'Empresa, nombre y contraseña son obligatorios'
    return
  }
  saving.value = true
  formError.value = null
  try {
    await bovedaStore.createCredencial({
      id_empresa: form.value.id_empresa,
      nombre: form.value.nombre,
      usuario_acceso: form.value.usuario_acceso || undefined,
      password_plain: form.value.password_plain,
      url: form.value.url || undefined,
      notas: form.value.notas || undefined,
    })
    showCreateModal.value = false
    resetForm()
  } catch (e: unknown) {
    const err = e as { response?: { status?: number; data?: { detail?: string } } }
    if (err.response?.status === 403) mfaRequired.value = true
    formError.value = err.response?.data?.detail ?? bovedaError.value ?? 'No se pudo crear la credencial'
  } finally {
    saving.value = false
  }
}

async function handleReveal(id: number): Promise<void> {
  revealing.value = true
  formError.value = null
  try {
    revealData.value = await bovedaStore.revealCredencial(id)
    showRevealModal.value = true
  } catch (e: unknown) {
    const err = e as { response?: { status?: number; data?: { detail?: string } } }
    if (err.response?.status === 403) {
      mfaRequired.value = true
      formError.value = 'Necesitas una sesión MFA verificada para revelar contraseñas'
      return
    }
    formError.value = err.response?.data?.detail ?? bovedaError.value ?? 'No se pudo revelar la credencial'
  } finally {
    revealing.value = false
  }
}

function closeRevealModal(): void {
  showRevealModal.value = false
  revealData.value = null
}

onMounted(loadData)


</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3">
      <div class="p-2 bg-gray-800 rounded-xl">
        <Lock class="text-white" :size="22" />
      </div>
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Bóveda de Credenciales</h1>
        <p class="text-gray-500 text-sm mt-1">Credenciales B2B cifradas con AES-256-GCM</p>
      </div>
    </div>

    <div class="flex justify-end">
      <Button @click="showCreateModal = true">
        <Plus :size="14" class="mr-2" />
        Nueva credencial
      </Button>
    </div>

    <div v-if="mfaRequired" class="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-3">
      <span class="text-2xl">🔒</span>
      <div>
        <p class="font-semibold text-amber-800">MFA requerido</p>
        <p class="text-sm text-amber-700">Necesitas tener MFA activo para acceder a la bóveda.</p>
      </div>
    </div>

    <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>

    <Card :padding="false">
      <div v-if="!loading && !bovedaLoading && credenciales.length === 0" class="text-center py-10 text-sm text-gray-500">
        No hay credenciales registradas todavía. Crea la primera desde “Nueva credencial”.
      </div>
      <Table v-else :columns="columns" :rows="credenciales.map((c) => ({ ...c, id: c.id_credencial }))" :loading="loading || bovedaLoading">
        <template #id_empresa="{ value }">
          <span>{{ getEmpresaNombre(Number(value)) }}</span>
        </template>
        <template #url="{ value }">
          <a v-if="value" :href="String(value)" target="_blank" class="text-blue-600 hover:underline text-xs truncate block max-w-[200px]">
            {{ value }}
          </a>
          <span v-else class="text-gray-400">—</span>
        </template>
        <template #acciones="{ row }">
          <button
            :disabled="revealing"
            @click.stop="handleReveal(Number((row as Record<string, unknown>).id_credencial))"
            class="px-2 py-1 text-xs bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-60 inline-flex items-center gap-1"
            title="Revelar contraseña"
          >
            <Eye :size="12" />
            Revelar
          </button>
        </template>
      </Table>
    </Card>

    <Modal :open="showCreateModal" title="Nueva credencial" size="md" @close="showCreateModal = false; resetForm()">
      <form class="space-y-3" @submit.prevent="handleCreate">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Empresa *</label>
          <select v-model.number="form.id_empresa" required class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white">
            <option :value="0">Selecciona una empresa</option>
            <option v-for="empresa in empresas" :key="empresa.id_cliente" :value="empresa.id_cliente">{{ empresa.nombre }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
          <input v-model="form.nombre" type="text" required class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" placeholder="Servidor, Portal SAT, ERP cliente..." />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Usuario</label>
          <input v-model="form.usuario_acceso" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Contraseña *</label>
          <input v-model="form.password_plain" type="password" required class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">URL</label>
          <input v-model="form.url" type="url" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Notas</label>
          <textarea v-model="form.notas" rows="2" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none" />
        </div>
        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" @click="showCreateModal = false; resetForm()">Cancelar</Button>
          <Button type="submit" :loading="saving">Guardar</Button>
        </div>
      </form>
    </Modal>

    <Modal :open="showRevealModal" title="Contraseña revelada" size="sm" @close="closeRevealModal">
      <div class="space-y-3" v-if="revealData">
        <p class="text-xs text-gray-500">{{ revealData.nombre }} · {{ getEmpresaNombre(revealData.id_empresa) }}</p>
        <div class="bg-gray-100 border border-gray-200 rounded-lg px-3 py-2 font-mono text-sm break-all">
          {{ revealData.password_plain }}
        </div>
        <p class="text-xs text-amber-700">Este acceso queda registrado en auditoría.</p>
      </div>
    </Modal>
  </div>
</template>

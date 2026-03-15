<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Plus, Wallet, TrendingDown, TrendingUp, Trash2 } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import api from '../services/api'
import type { CajaChicaResumen, MovimientoCajaChica, TipoMovimientoCaja } from '../types'

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const carryingOver = ref(false)
const showCreateModal = ref(false)
const showDeleteModal = ref(false)
const formError = ref<string | null>(null)
const carryoverError = ref<string | null>(null)
const selectedDeleteId = ref<number | null>(null)

const resumen = ref<CajaChicaResumen>({
  balance_actual: 0,
  ingresos_mes: 0,
  egresos_mes: 0,
  movimientos_mes: 0,
  fondo_mensual: 0,
  disponible_mes: 0,
})

const movimientos = ref<MovimientoCajaChica[]>([])

const form = ref({
  tipo: 'egreso' as TipoMovimientoCaja,
  concepto: '',
  categoria: '',
  monto: 0,
  responsable: '',
  observacion: '',
})

const columns = [
  { key: 'fecha', label: 'Fecha', class: 'w-40' },
  { key: 'tipo', label: 'Tipo', class: 'w-28' },
  { key: 'concepto', label: 'Concepto' },
  { key: 'categoria', label: 'Categoría', class: 'w-36' },
  { key: 'monto', label: 'Monto', class: 'w-32' },
  { key: 'acciones', label: 'Acciones', class: 'w-20' },
]

const rows = computed(() =>
  movimientos.value.map((m: MovimientoCajaChica) => ({
    ...m,
    id: m.id_movimiento,
    fecha: new Date(m.fecha).toLocaleString('es-EC'),
  }))
)

function formatUSD(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

async function loadData() {
  loading.value = true
  try {
    const movRes = await api.get<MovimientoCajaChica[]>('/api/v1/caja-chica/')
    const resumenRes = await api.get<CajaChicaResumen>('/api/v1/caja-chica/resumen')
    movimientos.value = movRes.data
    resumen.value = resumenRes.data
  } catch {
    formError.value = 'No se pudo cargar caja chica'
  } finally {
    loading.value = false
  }
}

async function createMovimiento() {
  saving.value = true
  formError.value = null
  try {
    await api.post('/api/v1/caja-chica/', {
      ...form.value,
      categoria: form.value.categoria || undefined,
      responsable: form.value.responsable || undefined,
      observacion: form.value.observacion || undefined,
    })
    showCreateModal.value = false
    form.value = {
      tipo: 'egreso',
      concepto: '',
      categoria: '',
      monto: 0,
      responsable: '',
      observacion: '',
    }
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'No se pudo registrar movimiento'
  } finally {
    saving.value = false
  }
}

function openDelete(id: number): void {
  selectedDeleteId.value = id
  showDeleteModal.value = true
}

async function deleteMovimiento() {
  if (!selectedDeleteId.value) return
  deleting.value = true
  formError.value = null
  try {
    await api.delete(`/api/v1/caja-chica/${selectedDeleteId.value}`)
    showDeleteModal.value = false
    selectedDeleteId.value = null
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'No se pudo eliminar movimiento'
  } finally {
    deleting.value = false
  }
}

async function cuadrarMesAnterior() {
  carryingOver.value = true
  carryoverError.value = null
  try {
    await api.post('/api/v1/caja-chica/cuadre-mes-anterior')
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    carryoverError.value = err.response?.data?.detail ?? 'No se pudo cuadrar con el mes anterior'
  } finally {
    carryingOver.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Caja Chica</h1>
        <p class="text-gray-500 text-sm mt-1">Control diario de ingresos, egresos y balance operativo</p>
      </div>
      <div class="flex items-center gap-2">
        <Button variant="secondary" :loading="carryingOver" @click="cuadrarMesAnterior">
          Cuadrar mes anterior
        </Button>
        <Button @click="showCreateModal = true; formError = null">
          <Plus :size="16" class="mr-2" />
          Nuevo movimiento
        </Button>
      </div>
    </div>

    <p v-if="carryoverError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ carryoverError }}</p>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card>
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-blue-50"><Wallet class="text-blue-600" :size="18" /></div>
          <div>
            <p class="text-xs text-gray-500">Balance actual</p>
            <p class="text-lg font-semibold" :class="resumen.balance_actual >= 0 ? 'text-emerald-700' : 'text-red-600'">{{ formatUSD(resumen.balance_actual) }}</p>
          </div>
        </div>
      </Card>
      <Card>
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-emerald-50"><TrendingUp class="text-emerald-600" :size="18" /></div>
          <div>
            <p class="text-xs text-gray-500">Ingresos del mes</p>
            <p class="text-lg font-semibold text-emerald-700">{{ formatUSD(resumen.ingresos_mes) }}</p>
          </div>
        </div>
      </Card>
      <Card>
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-red-50"><TrendingDown class="text-red-600" :size="18" /></div>
          <div>
            <p class="text-xs text-gray-500">Egresos del mes</p>
            <p class="text-lg font-semibold text-red-600">{{ formatUSD(resumen.egresos_mes) }}</p>
          </div>
        </div>
      </Card>
      <Card>
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-indigo-50"><Wallet class="text-indigo-600" :size="18" /></div>
          <div>
            <p class="text-xs text-gray-500">Disponible del mes</p>
            <p class="text-lg font-semibold" :class="resumen.disponible_mes >= 0 ? 'text-indigo-700' : 'text-red-600'">
              {{ formatUSD(resumen.disponible_mes) }}
            </p>
            <p class="text-[11px] text-gray-500">Base: {{ formatUSD(resumen.fondo_mensual) }}</p>
          </div>
        </div>
      </Card>
    </div>

    <Card :padding="false">
      <div class="p-4 border-b border-gray-100 text-sm text-gray-500">
        {{ resumen.movimientos_mes }} movimiento(s) este mes
      </div>
      <Table :columns="columns" :rows="rows" :loading="loading">
        <template #tipo="{ value }">
          <span class="px-2 py-1 rounded-md text-xs font-medium" :class="value === 'ingreso' ? 'bg-emerald-50 text-emerald-700' : value === 'egreso' ? 'bg-red-50 text-red-700' : 'bg-gray-100 text-gray-700'">
            {{ value }}
          </span>
        </template>
        <template #monto="{ row }">
          <span :class="String((row as Record<string, unknown>).tipo) === 'ingreso' ? 'text-emerald-700 font-medium' : 'text-red-600 font-medium'">
            {{ formatUSD(Number((row as Record<string, unknown>).monto ?? 0)) }}
          </span>
        </template>
        <template #acciones="{ row }">
          <button
            @click.stop="openDelete(Number((row as Record<string, unknown>).id_movimiento))"
            class="p-2 text-red-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            title="Eliminar"
          >
            <Trash2 :size="14" />
          </button>
        </template>
      </Table>
    </Card>

    <Modal :open="showCreateModal" title="Nuevo movimiento de caja" size="md" @close="showCreateModal = false">
      <form class="space-y-3" @submit.prevent="createMovimiento">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Tipo *</label>
            <select v-model="form.tipo" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white">
              <option value="ingreso">Ingreso</option>
              <option value="egreso">Egreso</option>
              <option value="ajuste">Ajuste</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Monto *</label>
            <input v-model.number="form.monto" type="number" min="0.01" step="0.01" required class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Concepto *</label>
            <input v-model="form.concepto" type="text" required class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Categoría</label>
            <input v-model="form.categoria" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Responsable</label>
            <input v-model="form.responsable" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Observación</label>
            <textarea v-model="form.observacion" rows="2" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none" />
          </div>
        </div>

        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>

        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" @click="showCreateModal = false; formError = null">Cancelar</Button>
          <Button type="submit" :loading="saving">Guardar</Button>
        </div>
      </form>
    </Modal>

    <Modal :open="showDeleteModal" title="Eliminar movimiento" size="sm" @close="showDeleteModal = false">
      <div class="space-y-4">
        <p class="text-sm text-gray-600">¿Seguro que deseas eliminar este movimiento?</p>
        <div class="flex justify-end gap-3">
          <Button variant="secondary" type="button" @click="showDeleteModal = false">Cancelar</Button>
          <Button :loading="deleting" @click="deleteMovimiento">Eliminar</Button>
        </div>
      </div>
    </Modal>
  </div>
</template>

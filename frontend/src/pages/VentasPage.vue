<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Plus, Search, Trash2, Receipt } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import { useVentasStore } from '../stores/ventas'
import { useClienteStore } from '../stores/clientes'
import { useInventarioStore } from '../stores/inventario'
import type { EstadoCotizacion } from '../types'

const ventasStore = useVentasStore()
const clienteStore = useClienteStore()
const inventarioStore = useInventarioStore()

const showCreateModal = ref(false)
const showFacturarModal = ref(false)
const showDeleteModal = ref(false)
const facturarId = ref<number | null>(null)
const deleteId = ref<number | null>(null)
const numeroFactura = ref('')
const saving = ref(false)
const deleting = ref(false)
const formError = ref<string | null>(null)
const clienteSearch = ref('')
const productoSearch = ref('')
const filterEstado = ref<EstadoCotizacion | 'all'>('all')

interface LineItem {
  id_producto: number
  nombre: string
  cantidad: number
  precio_unitario: number
  descuento: number
}

const form = ref({
  id_cliente: 0,
  notas: '',
  items: [] as LineItem[],
})

const clientesFiltered = computed(() =>
  clienteStore.clientes.filter((c) => {
    const q = clienteSearch.value.toLowerCase()
    const nombre = c.empresa?.razon_social ?? c.cliente_b2c?.nombre_completo ?? ''
    return nombre.toLowerCase().includes(q)
  }).slice(0, 8)
)

const productosFiltered = computed(() =>
  inventarioStore.productos.filter((p) => {
    const q = productoSearch.value.toLowerCase()
    return p.nombre.toLowerCase().includes(q) || p.codigo.toLowerCase().includes(q)
  }).slice(0, 8)
)

const lineSubtotal = (item: LineItem) =>
  item.cantidad * item.precio_unitario * (1 - item.descuento / 100)

const formSubtotal = computed(() => form.value.items.reduce((s, i) => s + lineSubtotal(i), 0))
const formImpuesto = computed(() => formSubtotal.value * 0.15)
const formTotal = computed(() => formSubtotal.value + formImpuesto.value)

const columns = [
  { key: 'numero', label: 'Número', class: 'w-36' },
  { key: 'id_cliente', label: 'Cliente ID', class: 'w-24' },
  { key: 'estado', label: 'Estado', class: 'w-32' },
  { key: 'total', label: 'Total', class: 'w-32' },
  { key: 'fecha_creacion', label: 'Fecha', class: 'w-32' },
  { key: 'acciones', label: '', class: 'w-24' },
]

const estadoVariant: Record<string, 'default' | 'info' | 'success' | 'warning' | 'danger'> = {
  borrador: 'default', enviada: 'info', aprobada: 'success', rechazada: 'danger', facturada: 'success',
}

const estadoLabels: Record<string, string> = {
  borrador: 'Borrador', enviada: 'Enviada', aprobada: 'Aprobada', rechazada: 'Rechazada', facturada: 'Facturada',
}

const pipelineCount = computed(() => {
  const counts: Record<string, number> = {}
  ventasStore.cotizaciones.forEach((c) => {
    counts[c.estado] = (counts[c.estado] ?? 0) + 1
  })
  return counts
})

const pipelineStages: Record<string, { label: string; color: string }> = {
  borrador: { label: 'Borrador', color: 'bg-gray-100 border-gray-300 text-gray-700' },
  enviada: { label: 'Enviada', color: 'bg-blue-50 border-blue-300 text-blue-700' },
  aprobada: { label: 'Aprobada', color: 'bg-emerald-50 border-emerald-300 text-emerald-700' },
  facturada: { label: 'Facturada', color: 'bg-cyan-50 border-cyan-300 text-cyan-700' },
}

const filteredRows = computed(() =>
  ventasStore.cotizaciones
    .filter((c) => filterEstado.value === 'all' || c.estado === filterEstado.value)
    .map((c) => ({
      ...c,
      id: c.id_cotizacion,
      total: `$${Number(c.total).toFixed(2)}`,
      fecha_creacion: new Date(c.fecha_creacion).toLocaleDateString('en-US'),
    }))
)

const selectedCliente = computed(() =>
  clienteStore.clientes.find((c) => c.id_cliente === form.value.id_cliente)
)

onMounted(async () => {
  await Promise.all([
    ventasStore.fetchCotizaciones(),
    clienteStore.fetchClientes(),
    inventarioStore.fetchProductos(),
  ])
})

function addProducto(p: typeof inventarioStore.productos[0]): void {
  const existing = form.value.items.find((i) => i.id_producto === p.id_producto)
  if (existing) {
    existing.cantidad++
  } else {
    form.value.items.push({
      id_producto: p.id_producto,
      nombre: p.nombre,
      cantidad: 1,
      precio_unitario: p.precio_venta,
      descuento: 0,
    })
  }
  productoSearch.value = ''
}

function removeItem(idx: number): void {
  form.value.items.splice(idx, 1)
}

function selectCliente(id: number): void {
  form.value.id_cliente = id
  clienteSearch.value = ''
}

async function handleCreate(): Promise<void> {
  if (!form.value.id_cliente) { formError.value = 'Selecciona un cliente'; return }
  if (form.value.items.length === 0) { formError.value = 'Agrega al menos un producto'; return }
  saving.value = true
  formError.value = null
  try {
    await ventasStore.createCotizacion({
      id_cliente: form.value.id_cliente,
      notas: form.value.notas || undefined,
      detalles: form.value.items.map((i) => ({
        id_producto: i.id_producto,
        cantidad: i.cantidad,
        precio_unitario: i.precio_unitario,
        descuento: i.descuento,
      })),
    })
    showCreateModal.value = false
    resetForm()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al crear cotización'
  } finally {
    saving.value = false
  }
}

async function handleEstadoChange(id: number, estado: string): Promise<void> {
  await ventasStore.updateEstado(id, estado)
}

function openFacturar(id: number): void {
  facturarId.value = id
  numeroFactura.value = `FAC-${String(id).padStart(6, '0')}`
  showFacturarModal.value = true
}

function openDelete(id: number): void {
  deleteId.value = id
  formError.value = null
  showDeleteModal.value = true
}

async function handleFacturar(): Promise<void> {
  if (!facturarId.value || !numeroFactura.value) return
  saving.value = true
  try {
    await ventasStore.facturar(facturarId.value, numeroFactura.value)
    showFacturarModal.value = false
    facturarId.value = null
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al facturar'
  } finally {
    saving.value = false
  }
}

async function handleDelete(): Promise<void> {
  if (!deleteId.value) return
  deleting.value = true
  formError.value = null
  try {
    await ventasStore.deleteCotizacion(deleteId.value)
    showDeleteModal.value = false
    deleteId.value = null
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al eliminar cotización'
  } finally {
    deleting.value = false
  }
}

function resetForm(): void {
  form.value = { id_cliente: 0, notas: '', items: [] }
  clienteSearch.value = ''
  productoSearch.value = ''
  formError.value = null
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Ventas & Cotizaciones</h1>
        <p class="text-gray-500 text-sm mt-1">Pipeline de ventas y facturación</p>
      </div>
      <Button @click="showCreateModal = true">
        <Plus :size="16" class="mr-2" />
        Nueva Cotización
      </Button>
    </div>

    <!-- Pipeline Mini -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <button
        v-for="(stage, key) in pipelineStages"
        :key="key"
        @click="filterEstado = filterEstado === key ? 'all' : key as EstadoCotizacion"
        :class="['rounded-xl border-2 p-3 text-left transition-all', stage.color, filterEstado === key ? 'ring-2 ring-offset-1 ring-blue-400' : '']"
      >
        <p class="text-2xl font-bold">{{ pipelineCount[key] ?? 0 }}</p>
        <p class="text-xs font-medium mt-1">{{ stage.label }}</p>
      </button>
    </div>

    <!-- Table -->
    <Card :padding="false">
      <div class="p-4 border-b border-gray-100 flex items-center gap-3">
        <span class="text-sm text-gray-500">
          {{ filteredRows.length }} cotización(es)
          <span v-if="filterEstado !== 'all'"> · Filtro: <strong>{{ estadoLabels[filterEstado] }}</strong></span>
        </span>
        <button v-if="filterEstado !== 'all'" @click="filterEstado = 'all'" class="text-xs text-blue-600 hover:underline">Limpiar filtro</button>
      </div>
      <Table :columns="columns" :rows="filteredRows" :loading="ventasStore.loading">
        <template #estado="{ value }">
          <div class="flex items-center gap-2">
            <Badge :variant="estadoVariant[String(value)] ?? 'default'">{{ estadoLabels[String(value)] ?? value }}</Badge>
          </div>
        </template>
        <template #acciones="{ row }">
          <div class="flex gap-1">
            <button
              v-if="String((row as Record<string,unknown>).estado) !== 'facturada'"
              @click.stop="openFacturar(Number((row as Record<string,unknown>).id_cotizacion))"
              class="p-1.5 text-xs bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors"
              title="Facturar"
            >
              <Receipt :size="13" />
            </button>
            <select
              v-if="String((row as Record<string,unknown>).estado) !== 'facturada'"
              @click.stop
              class="text-xs border border-gray-200 rounded-lg px-1 py-1 bg-white"
              :value="(row as Record<string,unknown>).estado"
              @change="(e) => handleEstadoChange(Number((row as Record<string,unknown>).id_cotizacion), (e.target as HTMLSelectElement).value)"
            >
              <option v-for="s in ['borrador','enviada','aprobada','rechazada']" :key="s" :value="s">{{ estadoLabels[s] }}</option>
            </select>
            <button
              v-if="String((row as Record<string,unknown>).estado) !== 'facturada'"
              @click.stop="openDelete(Number((row as Record<string,unknown>).id_cotizacion))"
              class="p-1.5 text-xs bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
              title="Eliminar cotización"
            >
              <Trash2 :size="13" />
            </button>
          </div>
        </template>
      </Table>
    </Card>

    <!-- Create Cotizacion Modal -->
    <Modal :open="showCreateModal" title="Nueva Cotización" size="xl" @close="showCreateModal = false; resetForm()">
      <form @submit.prevent="handleCreate" class="space-y-5">

        <!-- Client selector -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Cliente *</label>
          <div v-if="selectedCliente" class="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-sm">
            <span class="font-medium text-blue-800">
              {{ selectedCliente.empresa?.razon_social ?? selectedCliente.cliente_b2c?.nombre_completo }}
            </span>
            <button type="button" @click="form.id_cliente = 0" class="text-blue-500 hover:text-red-500 ml-2">✕</button>
          </div>
          <div v-else>
            <input
              v-model="clienteSearch"
              type="text"
              placeholder="Buscar cliente por nombre..."
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
            <div v-if="clienteSearch && clientesFiltered.length > 0" class="border border-gray-200 rounded-lg mt-1 bg-white shadow-lg divide-y divide-gray-50 max-h-48 overflow-y-auto">
              <button
                v-for="c in clientesFiltered"
                :key="c.id_cliente"
                type="button"
                @click="selectCliente(c.id_cliente)"
                class="w-full text-left px-3 py-2 text-sm hover:bg-blue-50 transition-colors"
              >
                {{ c.empresa?.razon_social ?? c.cliente_b2c?.nombre_completo }}
                <span class="text-xs text-gray-400 ml-2">ID #{{ c.id_cliente }}</span>
              </button>
            </div>
            <p v-if="clienteSearch && clientesFiltered.length === 0" class="text-xs text-gray-400 mt-1">Sin resultados</p>
          </div>
        </div>

        <!-- Product search and line items -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Productos</label>
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="14" />
            <input
              v-model="productoSearch"
              type="text"
              placeholder="Buscar producto por nombre o código..."
              class="w-full pl-9 pr-4 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div v-if="productoSearch && productosFiltered.length > 0" class="border border-gray-200 rounded-lg mt-1 bg-white shadow-lg max-h-40 overflow-y-auto">
            <button
              v-for="p in productosFiltered"
              :key="p.id_producto"
              type="button"
              @click="addProducto(p)"
              class="w-full text-left px-3 py-2 text-sm hover:bg-blue-50 transition-colors flex items-center justify-between"
            >
              <span>{{ p.nombre }} <span class="text-gray-400 text-xs">({{ p.codigo }})</span></span>
              <span class="text-blue-600 font-medium">${{ p.precio_venta.toFixed(2) }}</span>
            </button>
          </div>
        </div>

        <!-- Line items -->
        <div v-if="form.items.length > 0" class="border border-gray-200 rounded-xl overflow-hidden">
          <table class="min-w-full text-sm divide-y divide-gray-100">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Producto</th>
                <th class="px-3 py-2 text-center text-xs font-semibold text-gray-500 uppercase w-20">Cant.</th>
                <th class="px-3 py-2 text-right text-xs font-semibold text-gray-500 uppercase w-28">Precio</th>
                <th class="px-3 py-2 text-right text-xs font-semibold text-gray-500 uppercase w-20">Desc.%</th>
                <th class="px-3 py-2 text-right text-xs font-semibold text-gray-500 uppercase w-28">Subtotal</th>
                <th class="w-10"></th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-50">
              <tr v-for="(item, idx) in form.items" :key="idx">
                <td class="px-3 py-2 text-gray-700">{{ item.nombre }}</td>
                <td class="px-3 py-2">
                  <input v-model.number="item.cantidad" type="number" min="1" class="w-16 text-center px-1 py-1 border rounded text-xs focus:ring-1 focus:ring-blue-500 outline-none" />
                </td>
                <td class="px-3 py-2">
                  <input v-model.number="item.precio_unitario" type="number" min="0" step="0.01" class="w-24 text-right px-1 py-1 border rounded text-xs focus:ring-1 focus:ring-blue-500 outline-none" />
                </td>
                <td class="px-3 py-2">
                  <input v-model.number="item.descuento" type="number" min="0" max="100" class="w-16 text-right px-1 py-1 border rounded text-xs focus:ring-1 focus:ring-blue-500 outline-none" />
                </td>
                <td class="px-3 py-2 text-right font-medium">${{ lineSubtotal(item).toFixed(2) }}</td>
                <td class="px-3 py-2">
                  <button type="button" @click="removeItem(idx)" class="text-red-400 hover:text-red-600"><Trash2 :size="14" /></button>
                </td>
              </tr>
            </tbody>
            <tfoot class="bg-gray-50 text-sm">
              <tr>
                <td colspan="4" class="px-3 py-2 text-right text-gray-600">Subtotal</td>
                <td class="px-3 py-2 text-right font-semibold">${{ formSubtotal.toFixed(2) }}</td>
                <td></td>
              </tr>
              <tr>
                <td colspan="4" class="px-3 py-2 text-right text-gray-600">IVA (15%)</td>
                <td class="px-3 py-2 text-right font-semibold">${{ formImpuesto.toFixed(2) }}</td>
                <td></td>
              </tr>
              <tr class="text-base">
                <td colspan="4" class="px-3 py-2 text-right font-bold text-gray-800">Total</td>
                <td class="px-3 py-2 text-right font-bold text-blue-700">${{ formTotal.toFixed(2) }}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
        <p v-else class="text-sm text-gray-400 text-center py-3 border border-dashed border-gray-200 rounded-xl">
          Busca y agrega productos arriba
        </p>

        <!-- Notes -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Notas</label>
          <textarea v-model="form.notas" rows="2" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none" placeholder="Notas adicionales..." />
        </div>

        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>

        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" @click="showCreateModal = false; resetForm()">Cancelar</Button>
          <Button type="submit" :loading="saving">Crear Cotización</Button>
        </div>
      </form>
    </Modal>

    <!-- Facturar Modal -->
    <Modal :open="showFacturarModal" title="Facturar Cotización" size="sm" @close="showFacturarModal = false">
      <div class="space-y-4">
        <p class="text-sm text-gray-600">Ingresa el número de factura para completar la venta.</p>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Número de Factura *</label>
          <input v-model="numeroFactura" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" placeholder="FAC-000001" />
        </div>
        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>
        <div class="flex justify-end gap-3">
          <Button variant="secondary" type="button" @click="showFacturarModal = false">Cancelar</Button>
          <Button :loading="saving" @click="handleFacturar">Facturar</Button>
        </div>
      </div>
    </Modal>

    <Modal :open="showDeleteModal" title="Eliminar Cotización" size="sm" @close="showDeleteModal = false; formError = null">
      <div class="space-y-4">
        <p class="text-sm text-gray-600">Se eliminará la cotización seleccionada si todavía no fue facturada.</p>
        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>
        <div class="flex justify-end gap-3">
          <Button variant="secondary" type="button" @click="showDeleteModal = false">Cancelar</Button>
          <Button :loading="deleting" @click="handleDelete">Eliminar Cotización</Button>
        </div>
      </div>
    </Modal>
  </div>
</template>


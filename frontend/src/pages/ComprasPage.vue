<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Plus, Search, AlertTriangle, Package, CheckSquare, DollarSign, Boxes, TrendingUp, Trash2, ListTree, ScanLine } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import { useInventarioStore } from '../stores/inventario'
import { useAuthStore } from '../stores/auth'
import { useI18n } from 'vue-i18n'
import type { Inventario, InventarioSerie, EstadoSerie } from '../types'
import { formatUSD } from '../utils/currency'

const inventarioStore = useInventarioStore()
const auth = useAuthStore()
const { t } = useI18n()

const searchQuery = ref('')
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const showSeriesModal = ref(false)
const selectedProducto = ref<Inventario | null>(null)
const saving = ref(false)
const deleting = ref(false)
const seriesLoading = ref(false)
const serieSaving = ref(false)
const formError = ref<string | null>(null)
const seriesError = ref<string | null>(null)
const filterBajoStock = ref(false)

const canEdit = computed(() => auth.user?.rol === 'superadmin' || auth.user?.rol === 'administrativo_contable')

const categorias = ['hardware', 'software', 'accesorio', 'repuesto', 'licencia'] as const
const filterCategoria = ref<'all' | typeof categorias[number]>('all')

const createForm = ref({
  codigo: '',
  nombre: '',
  descripcion: '',
  categoria: 'hardware' as typeof categorias[number],
  precio_venta: 0,
  costo_adquisicion: 0,
  stock_actual: 0,
  stock_minimo: 0,
  requiere_serie: false,
})

const editForm = ref({
  codigo: '',
  nombre: '',
  descripcion: '',
  categoria: 'hardware' as typeof categorias[number],
  requiere_serie: false,
  stock_actual: 0,
  precio_venta: 0,
  costo_adquisicion: 0,
  stock_minimo: 0,
})

const serieForm = ref({
  numero_serie: '',
})

const columns = [
  { key: 'codigo', label: 'Código', class: 'w-28' },
  { key: 'nombre', label: 'Nombre' },
  { key: 'categoria', label: 'Categoría', class: 'w-28' },
  { key: 'estado_stock', label: 'Estado', class: 'w-28' },
  { key: 'stock_actual', label: 'Stock', class: 'w-24' },
  { key: 'stock_minimo', label: 'Mín.', class: 'w-20' },
  { key: 'costo_adquisicion', label: 'Costo', class: 'w-28' },
  { key: 'precio_venta', label: 'Precio', class: 'w-28' },
  { key: 'margen', label: 'Margen', class: 'w-24' },
  { key: 'acciones', label: '', class: 'w-28' },
]

const alertas = computed(() =>
  inventarioStore.productos.filter((p) => p.stock_actual <= p.stock_minimo)
)

const filteredRows = computed(() =>
  inventarioStore.productos
    .filter((p) => {
      if (filterBajoStock.value && p.stock_actual > p.stock_minimo) return false
      if (filterCategoria.value !== 'all' && p.categoria !== filterCategoria.value) return false
      if (!searchQuery.value) return true
      const q = searchQuery.value.toLowerCase()
      return p.nombre.toLowerCase().includes(q) || p.codigo.toLowerCase().includes(q)
    })
    .map((p) => ({
      ...p,
      id: p.id_producto,
      estado_stock: p.stock_actual <= p.stock_minimo ? 'Crítico' : p.stock_actual <= p.stock_minimo * 1.5 ? 'Bajo' : 'Saludable',
      costo_adquisicion: formatUSD(p.costo_adquisicion),
      precio_venta: formatUSD(p.precio_venta),
      margen: p.costo_adquisicion > 0 ? `${Math.round(((p.precio_venta - p.costo_adquisicion) / p.costo_adquisicion) * 100)}%` : '—',
    }))
)

const inventoryValue = computed(() =>
  inventarioStore.productos.reduce((sum, product) => sum + product.stock_actual * Number(product.costo_adquisicion ?? 0), 0)
)

const salesValue = computed(() =>
  inventarioStore.productos.reduce((sum, product) => sum + product.stock_actual * Number(product.precio_venta ?? 0), 0)
)

const averageMargin = computed(() => {
  const withCost = inventarioStore.productos.filter((product) => product.costo_adquisicion > 0)
  if (withCost.length === 0) return 0
  return withCost.reduce((sum, product) => sum + ((product.precio_venta - product.costo_adquisicion) / product.costo_adquisicion) * 100, 0) / withCost.length
})

const selectedSeries = computed<InventarioSerie[]>(() => {
  if (!selectedProducto.value) return []
  return inventarioStore.series[selectedProducto.value.id_producto] ?? []
})

onMounted(() => inventarioStore.fetchProductos())

function openEdit(row: Record<string, unknown>): void {
  if (!canEdit.value) return
  const p = inventarioStore.productos.find((x) => x.id_producto === row.id_producto)
  if (p) {
    selectedProducto.value = p
    editForm.value = {
      codigo: p.codigo,
      nombre: p.nombre,
      descripcion: p.descripcion ?? '',
      categoria: p.categoria as typeof categorias[number],
      requiere_serie: p.requiere_serie,
      stock_actual: p.stock_actual,
      precio_venta: p.precio_venta,
      costo_adquisicion: p.costo_adquisicion,
      stock_minimo: p.stock_minimo,
    }
    showEditModal.value = true
  }
}

async function handleCreate(): Promise<void> {
  saving.value = true
  formError.value = null
  try {
    await inventarioStore.createProducto({
      codigo: createForm.value.codigo,
      nombre: createForm.value.nombre,
      descripcion: createForm.value.descripcion || undefined,
      categoria: createForm.value.categoria,
      precio_venta: createForm.value.precio_venta,
      costo_adquisicion: createForm.value.costo_adquisicion,
      stock_actual: createForm.value.stock_actual,
      stock_minimo: createForm.value.stock_minimo,
      requiere_serie: createForm.value.requiere_serie,
    })
    showCreateModal.value = false
    resetCreateForm()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al crear producto'
  } finally {
    saving.value = false
  }
}

async function handleEdit(): Promise<void> {
  if (!selectedProducto.value) return
  saving.value = true
  formError.value = null
  try {
    await inventarioStore.updateProducto(selectedProducto.value.id_producto, {
      codigo: editForm.value.codigo,
      nombre: editForm.value.nombre,
      descripcion: editForm.value.descripcion || undefined,
      categoria: editForm.value.categoria,
      requiere_serie: editForm.value.requiere_serie,
      stock_actual: editForm.value.stock_actual,
      precio_venta: editForm.value.precio_venta,
      costo_adquisicion: editForm.value.costo_adquisicion,
      stock_minimo: editForm.value.stock_minimo,
    })
    showEditModal.value = false
    selectedProducto.value = null
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al actualizar producto'
  } finally {
    saving.value = false
  }
}

function stockVariant(actual: number, minimo: number): 'danger' | 'warning' | 'success' {
  if (actual <= minimo) return 'danger'
  if (actual <= minimo * 1.5) return 'warning'
  return 'success'
}

function openDelete(row: Record<string, unknown>): void {
  if (!canEdit.value) return
  const p = inventarioStore.productos.find((x) => x.id_producto === row.id_producto)
  if (!p) return
  selectedProducto.value = p
  formError.value = null
  showDeleteModal.value = true
}

async function handleDelete(): Promise<void> {
  if (!selectedProducto.value) return
  deleting.value = true
  formError.value = null
  try {
    await inventarioStore.deleteProducto(selectedProducto.value.id_producto)
    showDeleteModal.value = false
    showEditModal.value = false
    selectedProducto.value = null
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al eliminar producto'
  } finally {
    deleting.value = false
  }
}

async function openSeries(row: Record<string, unknown>): Promise<void> {
  const product = inventarioStore.productos.find((x) => x.id_producto === row.id_producto)
  if (!product) return
  selectedProducto.value = product
  showSeriesModal.value = true
  seriesError.value = null
  await loadSeries(product.id_producto)
}

async function loadSeries(idProducto: number): Promise<void> {
  seriesLoading.value = true
  try {
    await inventarioStore.fetchSeries(idProducto)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    seriesError.value = err.response?.data?.detail ?? 'Error al cargar series'
  } finally {
    seriesLoading.value = false
  }
}

async function handleCreateSerie(): Promise<void> {
  if (!selectedProducto.value || !serieForm.value.numero_serie) return
  serieSaving.value = true
  seriesError.value = null
  try {
    await inventarioStore.createSerie({
      id_producto: selectedProducto.value.id_producto,
      numero_serie: serieForm.value.numero_serie,
    })
    serieForm.value.numero_serie = ''
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    seriesError.value = err.response?.data?.detail ?? 'Error al registrar serie'
  } finally {
    serieSaving.value = false
  }
}

async function handleSerieStatusChange(idSerie: number, estado: EstadoSerie): Promise<void> {
  if (!selectedProducto.value) return
  try {
    await inventarioStore.updateSerie(idSerie, { estado }, selectedProducto.value.id_producto)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    seriesError.value = err.response?.data?.detail ?? 'Error al actualizar estado de serie'
  }
}

function resetCreateForm(): void {
  createForm.value = { codigo: '', nombre: '', descripcion: '', categoria: 'hardware', precio_venta: 0, costo_adquisicion: 0, stock_actual: 0, stock_minimo: 0, requiere_serie: false }
  formError.value = null
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="p-2 bg-orange-500 rounded-xl">
          <Package class="text-white" :size="22" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">{{ t('compras.title') }}</h1>
          <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">{{ t('compras.subtitle') }}</p>
        </div>
      </div>
      <Button v-if="canEdit" @click="showCreateModal = true">
        <Plus :size="16" class="mr-2" />
        {{ t('comprasPage.newProduct') }}
      </Button>
    </div>

    <div class="grid gap-4 md:grid-cols-4">
      <Card>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs uppercase tracking-wide text-gray-500">Productos</p>
            <p class="mt-2 text-2xl font-bold text-gray-900">{{ inventarioStore.productos.length }}</p>
          </div>
          <Boxes class="text-blue-600" :size="22" />
        </div>
      </Card>
      <Card>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs uppercase tracking-wide text-gray-500">Costo en inventario</p>
            <p class="mt-2 text-xl font-bold text-gray-900">{{ formatUSD(inventoryValue) }}</p>
          </div>
          <DollarSign class="text-emerald-600" :size="22" />
        </div>
      </Card>
      <Card>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs uppercase tracking-wide text-gray-500">Valor potencial venta</p>
            <p class="mt-2 text-xl font-bold text-gray-900">{{ formatUSD(salesValue) }}</p>
          </div>
          <TrendingUp class="text-cyan-600" :size="22" />
        </div>
      </Card>
      <Card>
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs uppercase tracking-wide text-gray-500">Margen promedio</p>
            <p class="mt-2 text-2xl font-bold text-gray-900">{{ averageMargin.toFixed(0) }}%</p>
          </div>
          <Package class="text-orange-500" :size="22" />
        </div>
      </Card>
    </div>

    <!-- Stock Alert Banner -->
    <div
      v-if="alertas.length > 0"
      class="flex items-start gap-3 bg-amber-50 border border-amber-300 rounded-xl px-4 py-3"
    >
      <AlertTriangle class="text-amber-500 shrink-0 mt-0.5" :size="18" />
      <div>
        <p class="text-sm font-semibold text-amber-800">
          {{ alertas.length }} producto(s) con stock crítico
        </p>
        <div class="flex flex-wrap gap-2 mt-1">
          <span
            v-for="p in alertas"
            :key="p.id_producto"
            class="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full"
          >
            {{ p.nombre }} ({{ p.stock_actual }}/{{ p.stock_minimo }})
          </span>
        </div>
      </div>
      <button
        @click="filterBajoStock = !filterBajoStock"
        :class="['ml-auto text-xs px-3 py-1.5 rounded-lg font-medium transition-colors', filterBajoStock ? 'bg-amber-500 text-white' : 'bg-amber-100 text-amber-700 hover:bg-amber-200']"
      >
        {{ filterBajoStock ? 'Mostrando críticos' : 'Filtrar críticos' }}
      </button>
    </div>

    <!-- Products Table -->
    <Card :padding="false">
      <div class="p-4 border-b border-gray-100 flex flex-wrap gap-3">
        <div class="relative flex-1 min-w-[200px]">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="15" />
          <input
            v-model="searchQuery"
            type="text"
            :placeholder="t('comprasPage.searchByNameOrCode')"
            class="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
        <select v-model="filterCategoria" class="px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:ring-2 focus:ring-blue-500 outline-none">
          <option value="all">{{ t('comprasPage.allCategories') }}</option>
          <option v-for="cat in categorias" :key="cat" :value="cat" class="capitalize">{{ cat }}</option>
        </select>
        <p class="text-xs text-gray-400 self-center">{{ filteredRows.length }} productos</p>
      </div>

      <Table
        :columns="columns"
        :rows="filteredRows"
        :loading="inventarioStore.loading"
        @row-click="openEdit"
      >
        <template #stock_actual="{ value, row }">
          <Badge :variant="stockVariant(Number(value), Number((row as Record<string, unknown>).stock_minimo))">
            {{ value }}
          </Badge>
        </template>
        <template #categoria="{ value }">
          <span class="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full capitalize">{{ value }}</span>
        </template>
        <template #estado_stock="{ value, row }">
          <Badge :variant="stockVariant(Number((row as Record<string, unknown>).stock_actual), Number((row as Record<string, unknown>).stock_minimo))">
            {{ value }}
          </Badge>
        </template>
        <template #margen="{ value }">
          <span class="font-medium text-gray-700">{{ value }}</span>
        </template>
        <template #acciones="{ row }">
          <div class="flex items-center gap-1">
            <button
              v-if="canEdit && Boolean((row as Record<string, unknown>).requiere_serie)"
              @click.stop="openSeries(row as Record<string, unknown>)"
              class="p-2 text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors"
              title="Gestionar series"
            >
              <ListTree :size="14" />
            </button>
            <button
              v-if="canEdit"
              @click.stop="openDelete(row as Record<string, unknown>)"
              class="p-2 text-red-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              title="Eliminar producto"
            >
              <Trash2 :size="14" />
            </button>
          </div>
        </template>
      </Table>
    </Card>

    <!-- Create Product Modal -->
    <Modal :open="showCreateModal" :title="t('comprasPage.newProduct')" size="md" @close="showCreateModal = false; resetCreateForm()">
      <form @submit.prevent="handleCreate" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Código *</label>
            <input v-model="createForm.codigo" required type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" placeholder="SKU-001" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Categoría *</label>
            <select v-model="createForm.categoria" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white">
              <option v-for="cat in categorias" :key="cat" :value="cat" class="capitalize">{{ cat }}</option>
            </select>
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
            <input v-model="createForm.nombre" required type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
            <textarea v-model="createForm.descripcion" rows="2" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Precio Venta (USD) *</label>
            <input v-model.number="createForm.precio_venta" required type="number" min="0" step="0.01" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Costo Adquisición *</label>
            <input v-model.number="createForm.costo_adquisicion" required type="number" min="0" step="0.01" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Stock Inicial</label>
            <input v-model.number="createForm.stock_actual" type="number" min="0" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Stock Mínimo</label>
            <input v-model.number="createForm.stock_minimo" type="number" min="0" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div class="col-span-2">
            <label class="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
              <input v-model="createForm.requiere_serie" type="checkbox" class="rounded text-blue-600" />
              Requiere número de serie
            </label>
          </div>
        </div>
        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>
        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" @click="showCreateModal = false; resetCreateForm()">{{ t('common.cancel') }}</Button>
          <Button type="submit" :loading="saving">{{ t('comprasPage.createProduct') }}</Button>
        </div>
      </form>
    </Modal>

    <!-- Edit Product Modal -->
    <Modal :open="showEditModal" :title="`Editar: ${selectedProducto?.nombre}`" size="md" @close="showEditModal = false; selectedProducto = null; formError = null">
      <form v-if="selectedProducto" @submit.prevent="handleEdit" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
            <input v-model="editForm.nombre" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
            <textarea v-model="editForm.descripcion" rows="2" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Código</label>
            <input v-model="editForm.codigo" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Categoría</label>
            <select v-model="editForm.categoria" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white">
              <option v-for="cat in categorias" :key="cat" :value="cat" class="capitalize">{{ cat }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Precio Venta (USD)</label>
            <input v-model.number="editForm.precio_venta" type="number" min="0" step="0.01" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Costo Adquisición (USD)</label>
            <input v-model.number="editForm.costo_adquisicion" type="number" min="0" step="0.01" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Stock Actual</label>
            <input v-model.number="editForm.stock_actual" type="number" min="0" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Stock Mínimo</label>
            <input v-model.number="editForm.stock_minimo" type="number" min="0" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div class="col-span-2">
            <label class="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
              <input v-model="editForm.requiere_serie" type="checkbox" class="rounded text-blue-600" />
              Requiere número de serie
            </label>
          </div>
        </div>
        <div class="flex items-center gap-2 text-sm text-gray-500 bg-gray-50 rounded-lg px-3 py-2">
          <CheckSquare :size="15" class="text-gray-400" />
          Stock actual: <span class="font-semibold text-gray-800">{{ selectedProducto.stock_actual }}</span> unidades
          <span class="text-xs text-gray-400 ml-1">(ajustado via series o ventas)</span>
        </div>
        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>
        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" class="mr-auto" @click="showDeleteModal = true">
            <Trash2 :size="14" class="mr-2" />
            Eliminar
          </Button>
          <Button variant="secondary" type="button" @click="showEditModal = false; selectedProducto = null">{{ t('common.cancel') }}</Button>
          <Button type="submit" :loading="saving">{{ t('comprasPage.saveChanges') }}</Button>
        </div>
      </form>
    </Modal>

    <Modal :open="showDeleteModal" :title="t('comprasPage.deleteProduct')" size="sm" @close="showDeleteModal = false; formError = null">
      <div class="space-y-4">
        <p class="text-sm text-gray-600">
          Vas a eliminar el producto <strong>{{ selectedProducto?.nombre }}</strong> del catálogo.
        </p>
        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>
        <div class="flex justify-end gap-3">
          <Button variant="secondary" type="button" @click="showDeleteModal = false">{{ t('common.cancel') }}</Button>
          <Button :loading="deleting" @click="handleDelete">{{ t('comprasPage.deleteProduct') }}</Button>
        </div>
      </div>
    </Modal>

    <Modal :open="showSeriesModal" :title="`Series: ${selectedProducto?.nombre}`" size="lg" @close="showSeriesModal = false; seriesError = null">
      <div class="space-y-4">
        <div v-if="selectedProducto" class="grid grid-cols-3 gap-3">
          <div class="rounded-xl bg-gray-50 px-3 py-2">
            <p class="text-xs text-gray-500">Código</p>
            <p class="text-sm font-semibold text-gray-900">{{ selectedProducto.codigo }}</p>
          </div>
          <div class="rounded-xl bg-gray-50 px-3 py-2">
            <p class="text-xs text-gray-500">Stock actual</p>
            <p class="text-sm font-semibold text-gray-900">{{ selectedProducto.stock_actual }}</p>
          </div>
          <div class="rounded-xl bg-gray-50 px-3 py-2">
            <p class="text-xs text-gray-500">Series registradas</p>
            <p class="text-sm font-semibold text-gray-900">{{ selectedSeries.length }}</p>
          </div>
        </div>

        <form @submit.prevent="handleCreateSerie" class="flex items-end gap-3">
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-700 mb-1">Nueva serie</label>
            <div class="relative">
              <ScanLine class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="15" />
              <input v-model="serieForm.numero_serie" type="text" class="w-full pl-9 pr-4 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" placeholder="SN-0001-XYZ" />
            </div>
          </div>
          <Button type="submit" :loading="serieSaving">Agregar Serie</Button>
        </form>

        <p v-if="seriesError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ seriesError }}</p>

        <div v-if="seriesLoading" class="text-sm text-gray-500">Cargando series...</div>
        <div v-else-if="selectedSeries.length === 0" class="text-sm text-gray-500 border border-dashed border-gray-200 rounded-xl px-4 py-6 text-center">
          Este producto aún no tiene series registradas.
        </div>
        <div v-else class="border border-gray-200 rounded-xl divide-y divide-gray-100 max-h-80 overflow-y-auto">
          <div v-for="serie in selectedSeries" :key="serie.id_serie" class="px-4 py-3 flex items-center justify-between gap-3">
            <div>
              <p class="text-sm font-medium text-gray-900">{{ serie.numero_serie }}</p>
              <p class="text-xs text-gray-500">Ingreso: {{ new Date(serie.fecha_ingreso).toLocaleDateString('en-US') }}</p>
            </div>
            <select
              :value="serie.estado"
              @change="handleSerieStatusChange(serie.id_serie, ($event.target as HTMLSelectElement).value as EstadoSerie)"
              class="px-3 py-2 text-sm border rounded-lg bg-white focus:ring-2 focus:ring-blue-500 outline-none"
            >
              <option value="disponible">Disponible</option>
              <option value="vendido">Vendido</option>
              <option value="en_reparacion">En reparación</option>
              <option value="baja">Baja</option>
            </select>
          </div>
        </div>
      </div>
    </Modal>
  </div>
</template>


<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Plus, Search, AlertTriangle, Package, CheckSquare } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import { useInventarioStore } from '../stores/inventario'
import { useAuthStore } from '../stores/auth'
import type { Inventario } from '../types'

const inventarioStore = useInventarioStore()
const auth = useAuthStore()

const searchQuery = ref('')
const showCreateModal = ref(false)
const showEditModal = ref(false)
const selectedProducto = ref<Inventario | null>(null)
const saving = ref(false)
const formError = ref<string | null>(null)
const filterBajoStock = ref(false)

const canEdit = computed(() => auth.user?.rol === 'admin' || auth.user?.rol === 'comprador')

const categorias = ['hardware', 'software', 'accesorio', 'repuesto', 'licencia'] as const

const createForm = ref({
  codigo: '',
  nombre: '',
  descripcion: '',
  categoria: 'hardware' as typeof categorias[number],
  precio_venta: 0,
  stock_minimo: 0,
  requiere_serie: false,
})

const editForm = ref({
  nombre: '',
  descripcion: '',
  precio_venta: 0,
  stock_minimo: 0,
})

const columns = [
  { key: 'codigo', label: 'Código', class: 'w-28' },
  { key: 'nombre', label: 'Nombre' },
  { key: 'categoria', label: 'Categoría', class: 'w-28' },
  { key: 'stock_actual', label: 'Stock', class: 'w-24' },
  { key: 'stock_minimo', label: 'Mín.', class: 'w-20' },
  { key: 'precio_venta', label: 'Precio (S/)', class: 'w-28' },
]

const alertas = computed(() =>
  inventarioStore.productos.filter((p) => p.stock_actual <= p.stock_minimo)
)

const filteredRows = computed(() =>
  inventarioStore.productos
    .filter((p) => {
      if (filterBajoStock.value && p.stock_actual > p.stock_minimo) return false
      if (!searchQuery.value) return true
      const q = searchQuery.value.toLowerCase()
      return p.nombre.toLowerCase().includes(q) || p.codigo.toLowerCase().includes(q)
    })
    .map((p) => ({
      ...p,
      id: p.id_producto,
      precio_venta: `S/ ${Number(p.precio_venta).toFixed(2)}`,
    }))
)

onMounted(() => inventarioStore.fetchProductos())

function openEdit(row: Record<string, unknown>): void {
  if (!canEdit.value) return
  const p = inventarioStore.productos.find((x) => x.id_producto === row.id_producto)
  if (p) {
    selectedProducto.value = p
    editForm.value = {
      nombre: p.nombre,
      descripcion: p.descripcion ?? '',
      precio_venta: p.precio_venta,
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
      stock_minimo: createForm.value.stock_minimo,
      requiere_serie: createForm.value.requiere_serie,
      costo_adquisicion: 0,
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
      nombre: editForm.value.nombre,
      descripcion: editForm.value.descripcion || undefined,
      precio_venta: editForm.value.precio_venta,
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

function resetCreateForm(): void {
  createForm.value = { codigo: '', nombre: '', descripcion: '', categoria: 'hardware', precio_venta: 0, stock_minimo: 0, requiere_serie: false }
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
          <h1 class="text-2xl font-bold text-gray-900">Compras & Inventario</h1>
          <p class="text-gray-500 text-sm mt-1">Control de stock y catálogo de productos</p>
        </div>
      </div>
      <Button v-if="canEdit" @click="showCreateModal = true">
        <Plus :size="16" class="mr-2" />
        Nuevo Producto
      </Button>
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
            placeholder="Buscar por nombre o código..."
            class="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
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
      </Table>
    </Card>

    <!-- Create Product Modal -->
    <Modal :open="showCreateModal" title="Nuevo Producto" size="md" @close="showCreateModal = false; resetCreateForm()">
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
            <label class="block text-sm font-medium text-gray-700 mb-1">Precio Venta (S/) *</label>
            <input v-model.number="createForm.precio_venta" required type="number" min="0" step="0.01" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
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
          <Button variant="secondary" type="button" @click="showCreateModal = false; resetCreateForm()">Cancelar</Button>
          <Button type="submit" :loading="saving">Crear Producto</Button>
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
            <label class="block text-sm font-medium text-gray-700 mb-1">Precio Venta (S/)</label>
            <input v-model.number="editForm.precio_venta" type="number" min="0" step="0.01" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Stock Mínimo</label>
            <input v-model.number="editForm.stock_minimo" type="number" min="0" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
        </div>
        <div class="flex items-center gap-2 text-sm text-gray-500 bg-gray-50 rounded-lg px-3 py-2">
          <CheckSquare :size="15" class="text-gray-400" />
          Stock actual: <span class="font-semibold text-gray-800">{{ selectedProducto.stock_actual }}</span> unidades
          <span class="text-xs text-gray-400 ml-1">(ajustado via series o ventas)</span>
        </div>
        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>
        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" @click="showEditModal = false; selectedProducto = null">Cancelar</Button>
          <Button type="submit" :loading="saving">Guardar Cambios</Button>
        </div>
      </form>
    </Modal>
  </div>
</template>


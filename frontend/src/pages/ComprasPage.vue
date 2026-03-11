<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Badge from '../components/ui/Badge.vue'
import api from '../services/api'
import type { Inventario } from '../types'

const productos = ref<Inventario[]>([])
const loading = ref(true)

const columns = [
  { key: 'codigo', label: 'Código' },
  { key: 'nombre', label: 'Nombre' },
  { key: 'categoria', label: 'Categoría' },
  { key: 'stock_actual', label: 'Stock' },
  { key: 'precio_venta', label: 'Precio (S/)' },
]

const rows = computed(() =>
  productos.value.map((p) => ({
    ...p,
    id: p.id_producto,
    precio_venta: `S/ ${Number(p.precio_venta).toFixed(2)}`,
  }))
)

onMounted(async () => {
  try {
    const { data } = await api.get<Inventario[]>('/api/v1/inventario/')
    productos.value = data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Compras & Inventario</h1>
        <p class="text-gray-500 text-sm mt-1">Control de stock y órdenes de compra</p>
      </div>
    </div>

    <Card :padding="false">
      <Table :columns="columns" :rows="rows" :loading="loading">
        <template #stock_actual="{ value, row }">
          <Badge
            :variant="Number(value) <= Number((row as Record<string, unknown>).stock_minimo) ? 'danger' : 'success'"
          >
            {{ value }}
          </Badge>
        </template>
      </Table>
    </Card>
  </div>
</template>

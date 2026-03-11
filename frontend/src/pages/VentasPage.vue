<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Plus } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import api from '../services/api'
import type { Cotizacion } from '../types'

const cotizaciones = ref<Cotizacion[]>([])
const loading = ref(true)

const columns = [
  { key: 'numero', label: 'Número' },
  { key: 'id_cliente', label: 'Cliente' },
  { key: 'estado', label: 'Estado' },
  { key: 'total', label: 'Total (S/)' },
  { key: 'fecha_creacion', label: 'Fecha' },
]

const estadoVariant: Record<string, 'default' | 'info' | 'success' | 'warning' | 'danger'> = {
  borrador: 'default',
  enviada: 'info',
  aprobada: 'success',
  rechazada: 'danger',
  facturada: 'success',
}

const rows = computed(() =>
  cotizaciones.value.map((c) => ({
    ...c,
    id: c.id_cotizacion,
    total: `S/ ${Number(c.total).toFixed(2)}`,
    fecha_creacion: new Date(c.fecha_creacion).toLocaleDateString('es-PE'),
  }))
)

onMounted(async () => {
  try {
    const { data } = await api.get<Cotizacion[]>('/api/v1/ventas/cotizaciones')
    cotizaciones.value = data
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Ventas & Cotizaciones</h1>
        <p class="text-gray-500 text-sm mt-1">Gestión de cotizaciones y facturación</p>
      </div>
      <Button>
        <Plus :size="16" class="mr-2" />
        Nueva Cotización
      </Button>
    </div>

    <Card :padding="false">
      <Table :columns="columns" :rows="rows" :loading="loading">
        <template #estado="{ value }">
          <Badge :variant="estadoVariant[String(value)] ?? 'default'">{{ value }}</Badge>
        </template>
      </Table>
    </Card>
  </div>
</template>

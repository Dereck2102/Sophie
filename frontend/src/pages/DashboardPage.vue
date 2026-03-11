<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Users, ShoppingCart, Wrench, AlertCircle } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Badge from '../components/ui/Badge.vue'
import api from '../services/api'
import type { Ticket } from '../types'

interface DashboardStats {
  total_clientes: number
  cotizaciones_mes: number
  tickets_abiertos: number
  productos_bajo_stock: number
}

const stats = ref<DashboardStats>({
  total_clientes: 0,
  cotizaciones_mes: 0,
  tickets_abiertos: 0,
  productos_bajo_stock: 0,
})

const recentTickets = ref<Ticket[]>([])
const loading = ref(true)

const statCards = [
  { label: 'Clientes Activos', key: 'total_clientes' as keyof DashboardStats, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
  { label: 'Cotizaciones (mes)', key: 'cotizaciones_mes' as keyof DashboardStats, icon: ShoppingCart, color: 'text-cyan-700', bg: 'bg-cyan-50' },
  { label: 'Tickets Abiertos', key: 'tickets_abiertos' as keyof DashboardStats, icon: Wrench, color: 'text-amber-600', bg: 'bg-amber-50' },
  { label: 'Stock Bajo', key: 'productos_bajo_stock' as keyof DashboardStats, icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-50' },
]

const priorityVariant: Record<string, 'danger' | 'warning' | 'info' | 'default'> = {
  critica: 'danger',
  alta: 'warning',
  media: 'info',
  baja: 'default',
}

const estadoVariant: Record<string, 'warning' | 'info' | 'success' | 'default'> = {
  abierto: 'warning',
  en_progreso: 'info',
  resuelto: 'success',
  cerrado: 'default',
}

onMounted(async () => {
  try {
    const [ticketRes] = await Promise.all([
      api.get<Ticket[]>('/api/v1/tickets/', { params: { limit: 5 } }),
    ])
    recentTickets.value = ticketRes.data
  } catch {
    // silently fail
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Dashboard</h1>
      <p class="text-gray-500 text-sm mt-1">Resumen del sistema SOPHIE</p>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <Card v-for="card in statCards" :key="card.key" :padding="false">
        <div class="p-5 flex items-center gap-4">
          <div :class="['p-3 rounded-xl', card.bg]">
            <component :is="card.icon" :class="['w-6 h-6', card.color]" />
          </div>
          <div>
            <p class="text-2xl font-bold text-gray-900">{{ stats[card.key] }}</p>
            <p class="text-sm text-gray-500">{{ card.label }}</p>
          </div>
        </div>
      </Card>
    </div>

    <!-- Recent Tickets -->
    <Card title="Tickets Recientes">
      <div v-if="loading" class="flex justify-center py-8">
        <svg class="animate-spin h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
      <div v-else-if="recentTickets.length === 0" class="text-center py-8 text-gray-400">
        No hay tickets recientes
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="ticket in recentTickets"
          :key="ticket.id_ticket"
          class="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-800 truncate">{{ ticket.titulo }}</p>
            <p class="text-xs text-gray-500">{{ ticket.numero }} · {{ ticket.tipo }}</p>
          </div>
          <div class="flex items-center gap-2 ml-4">
            <Badge :variant="priorityVariant[ticket.prioridad] ?? 'default'">{{ ticket.prioridad }}</Badge>
            <Badge :variant="estadoVariant[ticket.estado] ?? 'default'">{{ ticket.estado }}</Badge>
          </div>
        </div>
      </div>
    </Card>
  </div>
</template>

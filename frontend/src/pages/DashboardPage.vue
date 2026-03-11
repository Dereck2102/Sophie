<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Users, ShoppingCart, Wrench, AlertCircle, TrendingUp, FolderOpen,
  ArrowRight, Clock, XCircle
} from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Badge from '../components/ui/Badge.vue'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'
import type { Ticket } from '../types'

interface DashboardStats {
  total_clientes: number
  cotizaciones_mes: number
  tickets_abiertos: number
  productos_bajo_stock: number
  revenue_mes: number
  proyectos_activos: number
}

const router = useRouter()
const auth = useAuthStore()

const stats = ref<DashboardStats>({
  total_clientes: 0,
  cotizaciones_mes: 0,
  tickets_abiertos: 0,
  productos_bajo_stock: 0,
  revenue_mes: 0,
  proyectos_activos: 0,
})
const recentTickets = ref<Ticket[]>([])
const loading = ref(true)

const statCards = [
  {
    label: 'Clientes Activos', key: 'total_clientes' as keyof DashboardStats,
    icon: Users, color: 'text-blue-600', bg: 'bg-blue-50',
    link: '/crm', format: (v: number) => String(v)
  },
  {
    label: 'Ventas este Mes', key: 'revenue_mes' as keyof DashboardStats,
    icon: TrendingUp, color: 'text-emerald-600', bg: 'bg-emerald-50',
    link: '/ventas', format: (v: number) => `$${v.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
  },
  {
    label: 'Cotizaciones (mes)', key: 'cotizaciones_mes' as keyof DashboardStats,
    icon: ShoppingCart, color: 'text-cyan-700', bg: 'bg-cyan-50',
    link: '/ventas', format: (v: number) => String(v)
  },
  {
    label: 'Tickets Abiertos', key: 'tickets_abiertos' as keyof DashboardStats,
    icon: Wrench, color: 'text-amber-600', bg: 'bg-amber-50',
    link: '/taller', format: (v: number) => String(v)
  },
  {
    label: 'Proyectos Activos', key: 'proyectos_activos' as keyof DashboardStats,
    icon: FolderOpen, color: 'text-purple-600', bg: 'bg-purple-50',
    link: '/proyectos', format: (v: number) => String(v)
  },
  {
    label: 'Stock Bajo', key: 'productos_bajo_stock' as keyof DashboardStats,
    icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-50',
    link: '/compras', format: (v: number) => String(v)
  },
]

const priorityVariant: Record<string, 'danger' | 'warning' | 'info' | 'default'> = {
  critica: 'danger', alta: 'warning', media: 'info', baja: 'default',
}
const estadoVariant: Record<string, 'warning' | 'info' | 'success' | 'default'> = {
  abierto: 'warning', en_progreso: 'info', resuelto: 'success', cerrado: 'default',
}

const quickActions = computed(() => {
  const rol = auth.user?.rol
  const actions = []
  if (rol === 'admin' || rol === 'vendedor') {
    actions.push({ label: 'Nueva Cotización', icon: ShoppingCart, path: '/ventas', color: 'bg-blue-600 hover:bg-blue-700' })
    actions.push({ label: 'Nuevo Cliente', icon: Users, path: '/crm', color: 'bg-emerald-600 hover:bg-emerald-700' })
  }
  if (rol === 'admin' || rol === 'desarrollador' || rol === 'consultor_senior') {
    actions.push({ label: 'Nuevo Proyecto', icon: FolderOpen, path: '/proyectos', color: 'bg-purple-600 hover:bg-purple-700' })
  }
  if (rol === 'admin' || rol === 'tecnico_taller' || rol === 'tecnico_it') {
    actions.push({ label: 'Ver Mis Tickets', icon: Wrench, path: '/taller', color: 'bg-amber-600 hover:bg-amber-700' })
  }
  if (rol === 'admin' || rol === 'comprador') {
    actions.push({ label: 'Gestionar Stock', icon: AlertCircle, path: '/compras', color: 'bg-red-600 hover:bg-red-700' })
  }
  return actions
})

interface PipelineStage { label: string; estado: string; color: string; textColor: string }
const pipelineStages: PipelineStage[] = [
  { label: 'Borrador', estado: 'borrador', color: 'bg-gray-300', textColor: 'text-gray-600' },
  { label: 'Enviada', estado: 'enviada', color: 'bg-blue-400', textColor: 'text-blue-700' },
  { label: 'Aprobada', estado: 'aprobada', color: 'bg-emerald-400', textColor: 'text-emerald-700' },
  { label: 'Facturada', estado: 'facturada', color: 'bg-cyan-500', textColor: 'text-cyan-700' },
]
const cotizacionStats = ref<Record<string, number>>({})
const cotizacionTotal = computed(() => Object.values(cotizacionStats.value).reduce((a, b) => a + b, 0) || 1)

interface CotizacionSummary { estado: string }

async function loadData(): Promise<void> {
  try {
    const [statsRes, ticketRes, cotRes] = await Promise.all([
      api.get<DashboardStats>('/api/v1/dashboard/stats'),
      api.get<Ticket[]>('/api/v1/tickets/', { params: { limit: 6 } }),
      api.get<CotizacionSummary[]>('/api/v1/ventas/cotizaciones', { params: { limit: 200 } }),
    ])
    stats.value = statsRes.data
    recentTickets.value = ticketRes.data
    const counts: Record<string, number> = {}
    cotRes.data.forEach((c) => {
      counts[c.estado] = (counts[c.estado] ?? 0) + 1
    })
    cotizacionStats.value = counts
  } catch {
    // silently fail
  } finally {
    loading.value = false
  }
}

let refreshTimer: ReturnType<typeof setInterval> | null = null

/** Refresh interval for dashboard KPIs — balance between freshness and API load */
const DASHBOARD_REFRESH_MS = 60_000

onMounted(async () => {
  await loadData()
  refreshTimer = setInterval(loadData, DASHBOARD_REFRESH_MS)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">
          Bienvenido, {{ auth.user?.nombre_completo ?? auth.user?.username }} 👋
        </h1>
        <p class="text-gray-500 text-sm mt-1">
          {{ new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) }}
        </p>
      </div>
    </div>

    <!-- KPI Stats -->
    <div class="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      <router-link
        v-for="card in statCards"
        :key="card.key"
        :to="card.link"
        class="block"
      >
        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer">
          <div class="flex items-center gap-3 mb-2">
            <div :class="['p-2 rounded-lg', card.bg]">
              <component :is="card.icon" :class="['w-5 h-5', card.color]" />
            </div>
          </div>
          <p class="text-xl font-bold text-gray-900">{{ card.format(stats[card.key] as number) }}</p>
          <p class="text-xs text-gray-500 mt-1">{{ card.label }}</p>
        </div>
      </router-link>
    </div>

    <!-- Quick Actions -->
    <div v-if="quickActions.length > 0">
      <h2 class="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">Acciones Rápidas</h2>
      <div class="flex flex-wrap gap-3">
        <button
          v-for="action in quickActions"
          :key="action.path"
          @click="router.push(action.path)"
          :class="['flex items-center gap-2 px-4 py-2.5 text-white text-sm font-medium rounded-xl transition-colors', action.color]"
        >
          <component :is="action.icon" :size="16" />
          {{ action.label }}
        </button>
      </div>
    </div>

    <!-- Two column layout -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

      <!-- Recent Tickets -->
      <Card :padding="false">
        <div class="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h3 class="font-semibold text-gray-800">Tickets Recientes</h3>
          <router-link to="/taller" class="text-xs text-blue-600 hover:underline flex items-center gap-1">
            Ver todos <ArrowRight :size="12" />
          </router-link>
        </div>
        <div v-if="loading" class="flex justify-center py-8">
          <svg class="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
        <div v-else-if="recentTickets.length === 0" class="text-center py-8 text-gray-400 text-sm">
          No hay tickets recientes
        </div>
        <div v-else class="divide-y divide-gray-50">
          <div
            v-for="ticket in recentTickets"
            :key="ticket.id_ticket"
            class="flex items-center justify-between px-5 py-3 hover:bg-gray-50 transition-colors cursor-pointer"
            @click="router.push('/taller')"
          >
            <div class="flex-1 min-w-0 mr-3">
              <p class="text-sm font-medium text-gray-800 truncate">{{ ticket.titulo }}</p>
              <p class="text-xs text-gray-400 mt-0.5">{{ ticket.numero }}</p>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <Badge :variant="priorityVariant[ticket.prioridad] ?? 'default'">{{ ticket.prioridad }}</Badge>
              <Badge :variant="estadoVariant[ticket.estado] ?? 'default'">{{ ticket.estado.replace('_', ' ') }}</Badge>
            </div>
          </div>
        </div>
      </Card>

      <!-- Pipeline Summary -->
      <Card title="Pipeline de Ventas">
        <div class="space-y-3">
          <div
            v-for="stage in pipelineStages"
            :key="stage.estado"
          >
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm text-gray-600">{{ stage.label }}</span>
              <span class="text-xs font-semibold" :class="stage.textColor">{{ cotizacionStats[stage.estado] ?? 0 }}</span>
            </div>
            <div class="w-full bg-gray-100 rounded-full h-2">
              <div
                :class="['h-2 rounded-full transition-all', stage.color]"
                :style="`width: ${((cotizacionStats[stage.estado] ?? 0) / cotizacionTotal) * 100}%`"
              />
            </div>
          </div>
          <div class="pt-2 border-t border-gray-100">
            <router-link to="/ventas" class="text-sm text-blue-600 hover:underline flex items-center gap-1">
              Gestionar cotizaciones <ArrowRight :size="13" />
            </router-link>
          </div>
        </div>
      </Card>

    </div>

    <!-- Alerts row -->
    <div v-if="stats.productos_bajo_stock > 0 || stats.tickets_abiertos > 5" class="space-y-2">
      <div v-if="stats.productos_bajo_stock > 0" class="flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
        <XCircle class="text-red-500 shrink-0" :size="18" />
        <p class="text-sm text-red-700">
          <span class="font-semibold">{{ stats.productos_bajo_stock }} producto(s)</span> con stock por debajo del mínimo.
          <router-link to="/compras" class="underline ml-1">Gestionar inventario →</router-link>
        </p>
      </div>
      <div v-if="stats.tickets_abiertos > 5" class="flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
        <Clock class="text-amber-500 shrink-0" :size="18" />
        <p class="text-sm text-amber-700">
          <span class="font-semibold">{{ stats.tickets_abiertos }} tickets</span> abiertos requieren atención.
          <router-link to="/taller" class="underline ml-1">Ver tickets →</router-link>
        </p>
      </div>
    </div>

  </div>
</template>


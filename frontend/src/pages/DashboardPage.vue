<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Users, ShoppingCart, Wrench, AlertCircle, TrendingUp, FolderOpen,
  ArrowRight, Clock, XCircle, UserCog, Settings, Lock
} from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Badge from '../components/ui/Badge.vue'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'
import type { ConfiguracionSistema, Ticket } from '../types'

interface DashboardStats {
  total_clientes: number
  cotizaciones_mes: number
  tickets_abiertos: number
  productos_bajo_stock: number
  revenue_mes: number
  proyectos_activos: number
  margen_bruto_mes: number
  caja_chica_balance: number
  caja_chica_egresos_mes: number
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
  margen_bruto_mes: 0,
  caja_chica_balance: 0,
  caja_chica_egresos_mes: 0,
})
const recentTickets = ref<Ticket[]>([])
const loading = ref(true)

const financeInputs = ref({
  projectedSales: 12000,
  projectedCosts: 8000,
  ivaRate: 15,
  discountRate: 5,
  laborCost: 350,
  materialCost: 520,
  mobilityCost: 80,
  softwareCost: 120,
  technicalHours: 12,
  hourlyRate: 25,
})

const financeSummary = computed(() => {
  const labor = Number(financeInputs.value.laborCost) || 0
  const material = Number(financeInputs.value.materialCost) || 0
  const mobility = Number(financeInputs.value.mobilityCost) || 0
  const software = Number(financeInputs.value.softwareCost) || 0
  const hours = Number(financeInputs.value.technicalHours) || 0
  const hourly = Number(financeInputs.value.hourlyRate) || 0
  const discount = Math.max(0, Number(financeInputs.value.discountRate) || 0)
  const iva = Math.max(0, Number(financeInputs.value.ivaRate) || 0)
  const projectedSales = Number(financeInputs.value.projectedSales) || 0
  const projectedCosts = Number(financeInputs.value.projectedCosts) || 0

  const operationalCost = labor + material + mobility + software
  const technicalCost = hours * hourly
  const quoteSubtotal = operationalCost + technicalCost
  const discountValue = quoteSubtotal * (discount / 100)
  const taxableBase = Math.max(0, quoteSubtotal - discountValue)
  const ivaValue = taxableBase * (iva / 100)
  const quoteTotal = taxableBase + ivaValue
  const monthlyProfit = projectedSales - projectedCosts
  const annualProfit = monthlyProfit * 12
  const margin = projectedSales > 0 ? (monthlyProfit / projectedSales) * 100 : 0

  return {
    operationalCost,
    technicalCost,
    quoteSubtotal,
    discountValue,
    taxableBase,
    ivaValue,
    quoteTotal,
    monthlyProfit,
    annualProfit,
    margin,
  }
})

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value)
}

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
    label: 'Margen Bruto (Mes)', key: 'margen_bruto_mes' as keyof DashboardStats,
    icon: TrendingUp, color: 'text-emerald-700', bg: 'bg-emerald-50',
    link: '/ventas', format: (v: number) => `$${v.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
  },
  {
    label: 'Balance Caja Chica', key: 'caja_chica_balance' as keyof DashboardStats,
    icon: Lock, color: 'text-indigo-700', bg: 'bg-indigo-50',
    link: '/caja-chica', format: (v: number) => `$${v.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
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
  if (rol === 'superadmin' || rol === 'ejecutivo') {
    actions.push({ label: 'Nueva Cotización', icon: ShoppingCart, path: '/ventas', color: 'bg-blue-600 hover:bg-blue-700' })
    actions.push({ label: 'Nuevo Cliente', icon: Users, path: '/crm', color: 'bg-emerald-600 hover:bg-emerald-700' })
  }
  if (rol === 'superadmin' || rol === 'ejecutivo') {
    actions.push({ label: 'Nuevo Proyecto', icon: FolderOpen, path: '/proyectos', color: 'bg-purple-600 hover:bg-purple-700' })
  }
  if (rol === 'superadmin' || rol === 'ejecutivo' || rol === 'tecnico') {
    actions.push({ label: 'Ver Mis Tickets', icon: Wrench, path: '/taller', color: 'bg-amber-600 hover:bg-amber-700' })
  }
  if (rol === 'superadmin' || rol === 'administrativo_contable') {
    actions.push({ label: 'Gestionar Stock', icon: AlertCircle, path: '/compras', color: 'bg-red-600 hover:bg-red-700' })
  }
  if (rol === 'superadmin') {
    actions.push({ label: 'Administrar Usuarios', icon: UserCog, path: '/usuarios', color: 'bg-slate-700 hover:bg-slate-800' })
    actions.push({ label: 'Bóveda y Accesos', icon: Lock, path: '/boveda', color: 'bg-indigo-700 hover:bg-indigo-800' })
  }
  if (rol === 'superadmin') {
    actions.push({ label: 'Configuración ERP', icon: Settings, path: '/configuracion', color: 'bg-gray-700 hover:bg-gray-800' })
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
    const [statsRes, ticketRes, cotRes, settingsRes] = await Promise.all([
      api.get<DashboardStats>('/api/v1/dashboard/stats'),
      api.get<Ticket[]>('/api/v1/tickets/', { params: { limit: 6 } }),
      api.get<CotizacionSummary[]>('/api/v1/ventas/cotizaciones', { params: { limit: 200 } }),
      api.get<ConfiguracionSistema>('/api/v1/admin/settings/public'),
    ])
    stats.value = statsRes.data
    recentTickets.value = ticketRes.data
    financeInputs.value = {
      ...financeInputs.value,
      ivaRate: settingsRes.data.iva_default_percent ?? financeInputs.value.ivaRate,
      discountRate: settingsRes.data.descuento_default_percent ?? financeInputs.value.discountRate,
      hourlyRate: settingsRes.data.costo_hora_tecnica_default ?? financeInputs.value.hourlyRate,
      laborCost: settingsRes.data.costo_mano_obra_default ?? financeInputs.value.laborCost,
      materialCost: settingsRes.data.costo_material_default ?? financeInputs.value.materialCost,
      mobilityCost: settingsRes.data.costo_movilizacion_default ?? financeInputs.value.mobilityCost,
      softwareCost: settingsRes.data.costo_software_default ?? financeInputs.value.softwareCost,
    }
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

    <!-- Financial Projection Studio -->
    <Card title="Centro de Proyecciones y Costeo">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div class="space-y-3">
          <h3 class="text-sm font-semibold text-gray-700">Parámetros financieros</h3>
          <label class="block text-xs text-gray-500">Ventas proyectadas (mes)
            <input v-model.number="financeInputs.projectedSales" type="number" min="0" class="mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </label>
          <label class="block text-xs text-gray-500">Costos proyectados (mes)
            <input v-model.number="financeInputs.projectedCosts" type="number" min="0" class="mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </label>
          <label class="block text-xs text-gray-500">IVA (%)
            <input v-model.number="financeInputs.ivaRate" type="number" min="0" step="0.1" class="mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </label>
          <label class="block text-xs text-gray-500">Descuento (%)
            <input v-model.number="financeInputs.discountRate" type="number" min="0" step="0.1" class="mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </label>
        </div>

        <div class="space-y-3">
          <h3 class="text-sm font-semibold text-gray-700">Costos de cotización</h3>
          <label class="block text-xs text-gray-500">Mano de obra
            <input v-model.number="financeInputs.laborCost" type="number" min="0" class="mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </label>
          <label class="block text-xs text-gray-500">Materiales
            <input v-model.number="financeInputs.materialCost" type="number" min="0" class="mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </label>
          <label class="block text-xs text-gray-500">Movilización
            <input v-model.number="financeInputs.mobilityCost" type="number" min="0" class="mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </label>
          <label class="block text-xs text-gray-500">Software
            <input v-model.number="financeInputs.softwareCost" type="number" min="0" class="mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </label>
          <label class="block text-xs text-gray-500">Horas técnicas
            <input v-model.number="financeInputs.technicalHours" type="number" min="0" step="0.5" class="mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </label>
          <label class="block text-xs text-gray-500">Tarifa hora técnica
            <input v-model.number="financeInputs.hourlyRate" type="number" min="0" step="0.5" class="mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </label>
        </div>

        <div class="space-y-2">
          <h3 class="text-sm font-semibold text-gray-700">Resultados</h3>
          <div class="bg-gray-50 border rounded-lg p-3 space-y-1 text-sm">
            <div class="flex justify-between"><span class="text-gray-600">Costo operacional</span><span class="font-medium">{{ formatCurrency(financeSummary.operationalCost) }}</span></div>
            <div class="flex justify-between"><span class="text-gray-600">Costo técnico</span><span class="font-medium">{{ formatCurrency(financeSummary.technicalCost) }}</span></div>
            <div class="flex justify-between"><span class="text-gray-600">Subtotal cotización</span><span class="font-medium">{{ formatCurrency(financeSummary.quoteSubtotal) }}</span></div>
            <div class="flex justify-between"><span class="text-gray-600">Descuento</span><span class="font-medium text-amber-700">- {{ formatCurrency(financeSummary.discountValue) }}</span></div>
            <div class="flex justify-between"><span class="text-gray-600">Base imponible</span><span class="font-medium">{{ formatCurrency(financeSummary.taxableBase) }}</span></div>
            <div class="flex justify-between"><span class="text-gray-600">IVA</span><span class="font-medium">{{ formatCurrency(financeSummary.ivaValue) }}</span></div>
            <div class="flex justify-between border-t pt-2"><span class="text-gray-700 font-semibold">Total cotización</span><span class="font-bold text-blue-700">{{ formatCurrency(financeSummary.quoteTotal) }}</span></div>
          </div>
          <div class="bg-white border rounded-lg p-3 space-y-1 text-sm">
            <div class="flex justify-between"><span class="text-gray-600">Ganancia mensual</span><span :class="financeSummary.monthlyProfit >= 0 ? 'font-semibold text-emerald-700' : 'font-semibold text-red-600'">{{ formatCurrency(financeSummary.monthlyProfit) }}</span></div>
            <div class="flex justify-between"><span class="text-gray-600">Ganancia anual proyectada</span><span :class="financeSummary.annualProfit >= 0 ? 'font-semibold text-emerald-700' : 'font-semibold text-red-600'">{{ formatCurrency(financeSummary.annualProfit) }}</span></div>
            <div class="flex justify-between"><span class="text-gray-600">Margen (%)</span><span :class="financeSummary.margin >= 0 ? 'font-semibold text-emerald-700' : 'font-semibold text-red-600'">{{ financeSummary.margin.toFixed(2) }}%</span></div>
          </div>
        </div>
      </div>
    </Card>

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


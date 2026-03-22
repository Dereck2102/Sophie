<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  Briefcase,
  Clock,
  FolderOpen,
  Landmark,
  Receipt,
  ShoppingCart,
  TrendingDown,
  TrendingUp,
  Users,
  Wallet,
  Wrench,
  XCircle,
} from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Badge from '../components/ui/Badge.vue'
import { useAuthStore } from '../stores/auth'
import { useDashboardStore } from '../stores/dashboard'
import { useProyectoStore } from '../stores/proyectos'
import { useTicketStore } from '../stores/tickets'
import { useVentasStore } from '../stores/ventas'
import type { ProyectoEstadisticas, Ticket } from '../types'
import type { DashboardAlert, DashboardReceivableDueItem } from '../stores/dashboard'

interface PipelineStage {
  label: string
  estado: string
  color: string
  textColor: string
}

const router = useRouter()
const auth = useAuthStore()
const dashboardStore = useDashboardStore()
const proyectoStore = useProyectoStore()
const ticketStore = useTicketStore()
const ventasStore = useVentasStore()
const { stats, analytics } = storeToRefs(dashboardStore)

const recentTickets = ref<Ticket[]>([])
const cotizacionStats = ref<Record<string, number>>({})
const projectStats = ref<ProyectoEstadisticas[]>([])
const loading = ref(true)
const dashboardViewMode = ref<'all' | 'finance' | 'operations'>('all')
const selectedFinancialMetric = ref<string | null>(null)

const pipelineStages: PipelineStage[] = [
  { label: 'Borrador', estado: 'borrador', color: 'bg-slate-400', textColor: 'text-slate-700' },
  { label: 'Enviada', estado: 'enviada', color: 'bg-sky-500', textColor: 'text-sky-700' },
  { label: 'Aprobada', estado: 'aprobada', color: 'bg-emerald-500', textColor: 'text-emerald-700' },
  { label: 'Facturada', estado: 'facturada', color: 'bg-indigo-500', textColor: 'text-indigo-700' },
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

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value)
}

function formatCompactCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

const cotizacionTotal = computed(() => Object.values(cotizacionStats.value).reduce((sum, count) => sum + count, 0) || 1)

const financialCards = computed(() => [
  {
    label: 'Ingresos facturados',
    value: analytics.value.ingresos_facturados_mes,
    icon: TrendingUp,
    tone: 'text-emerald-700',
    bg: 'bg-emerald-50',
    link: '/ventas',
    detail: 'Ventas confirmadas del mes',
  },
  {
    label: 'Compras registradas',
    value: analytics.value.compras_registradas_mes,
    icon: Receipt,
    tone: 'text-rose-700',
    bg: 'bg-rose-50',
    link: '/compras',
    detail: 'Ordenes emitidas no canceladas',
  },
  {
    label: 'Flujo operativo',
    value: analytics.value.flujo_neto_mes,
    icon: analytics.value.flujo_neto_mes >= 0 ? Landmark : TrendingDown,
    tone: analytics.value.flujo_neto_mes >= 0 ? 'text-sky-700' : 'text-red-700',
    bg: analytics.value.flujo_neto_mes >= 0 ? 'bg-sky-50' : 'bg-red-50',
    link: '/flujo-operativo',
    detail: 'Ventas + caja menos compras y egresos',
  },
  {
    label: 'Cartera por cobrar',
    value: analytics.value.cuentas_por_cobrar,
    icon: Briefcase,
    tone: 'text-amber-700',
    bg: 'bg-amber-50',
    link: '/ventas',
    detail: 'Cotizaciones aprobadas o enviadas',
  },
  {
    label: 'Ordenes comprometidas',
    value: analytics.value.ordenes_pendientes_monto,
    icon: ShoppingCart,
    tone: 'text-fuchsia-700',
    bg: 'bg-fuchsia-50',
    link: '/compras',
    detail: 'Compras pendientes por cerrar',
  },
  {
    label: 'Caja chica disponible',
    value: analytics.value.caja_chica_balance,
    icon: Wallet,
    tone: analytics.value.caja_chica_balance >= 0 ? 'text-indigo-700' : 'text-red-700',
    bg: analytics.value.caja_chica_balance >= 0 ? 'bg-indigo-50' : 'bg-red-50',
    link: '/caja-chica',
    detail: 'Balance acumulado de movimientos',
  },
])

const operationalCards = computed(() => [
  {
    label: 'Clientes activos',
    value: String(stats.value.total_clientes),
    icon: Users,
    tone: 'text-blue-700',
    bg: 'bg-blue-50',
    link: '/ventas',
  },
  {
    label: 'Proyectos activos',
    value: String(stats.value.proyectos_activos),
    icon: FolderOpen,
    tone: 'text-violet-700',
    bg: 'bg-violet-50',
    link: '/proyectos',
  },
  {
    label: 'Tickets abiertos',
    value: String(stats.value.tickets_abiertos),
    icon: Wrench,
    tone: 'text-orange-700',
    bg: 'bg-orange-50',
    link: '/taller',
  },
  {
    label: 'Items bajo stock',
    value: String(stats.value.productos_bajo_stock),
    icon: Boxes,
    tone: 'text-red-700',
    bg: 'bg-red-50',
    link: '/compras',
  },
])

const trendMaxValue = computed(() => {
  const values = analytics.value.tendencia_mensual.flatMap((item) => [
    item.ingresos,
    item.compras,
    item.caja_egresos,
    Math.abs(item.flujo_neto),
  ])
  return Math.max(...values, 1)
})

const quickActions = computed(() => {
  const rol = auth.user?.rol
  const actions = [
    { label: 'Caja chica', path: '/caja-chica', color: 'bg-indigo-700 hover:bg-indigo-800', icon: Wallet },
    { label: 'Compras', path: '/compras', color: 'bg-rose-700 hover:bg-rose-800', icon: Receipt },
    { label: 'Ventas', path: '/ventas', color: 'bg-emerald-700 hover:bg-emerald-800', icon: TrendingUp },
  ]

  if (rol === 'superadmin' || rol === 'ejecutivo') {
    actions.push({ label: 'Proyectos', path: '/proyectos', color: 'bg-violet-700 hover:bg-violet-800', icon: FolderOpen })
  }

  if (rol === 'superadmin' || rol === 'ejecutivo' || rol === 'tecnico') {
    actions.push({ label: 'Taller', path: '/taller', color: 'bg-orange-700 hover:bg-orange-800', icon: Wrench })
  }

  return actions
})

const selectedFinancialCard = computed(() =>
  financialCards.value.find((card) => card.label === selectedFinancialMetric.value) ?? null
)

const showFinancialPanels = computed(() => dashboardViewMode.value === 'all' || dashboardViewMode.value === 'finance')
const showOperationalPanels = computed(() => dashboardViewMode.value === 'all' || dashboardViewMode.value === 'operations')

function selectFinancialMetric(label: string): void {
  selectedFinancialMetric.value = label
}

const projectStatsInFocus = computed(() =>
  [...projectStats.value]
    .sort((a, b) => b.porcentaje_completacion - a.porcentaje_completacion)
    .slice(0, 3)
)

function alertClass(severity: DashboardAlert['severity']): string {
  if (severity === 'critical') return 'border-red-200 bg-red-50 text-red-800'
  if (severity === 'warning') return 'border-amber-200 bg-amber-50 text-amber-800'
  return 'border-sky-200 bg-sky-50 text-sky-800'
}

function dueBadgeClass(item: DashboardReceivableDueItem): string {
  if ((item.dias_vencido ?? 0) > 0) return 'bg-red-100 text-red-700'
  if ((item.dias_para_vencer ?? 999) <= 3) return 'bg-amber-100 text-amber-700'
  return 'bg-emerald-100 text-emerald-700'
}

function correlationClass(status: string): string {
  if (status === 'critical') return 'border-red-200 bg-red-50 text-red-800'
  if (status === 'warning') return 'border-amber-200 bg-amber-50 text-amber-800'
  return 'border-emerald-200 bg-emerald-50 text-emerald-800'
}

async function loadData(): Promise<void> {
  try {
    await Promise.all([
      dashboardStore.fetchAll(false),
      proyectoStore.fetchProyectos(false),
      ticketStore.fetchTickets(false),
      ventasStore.fetchCotizaciones(false, 200),
    ])
    recentTickets.value = [...ticketStore.tickets]
      .sort((a, b) => new Date(b.fecha_creacion).getTime() - new Date(a.fecha_creacion).getTime())
      .slice(0, 6)

    const counts: Record<string, number> = {}
    ventasStore.cotizaciones.forEach((cotizacion) => {
      counts[cotizacion.estado] = (counts[cotizacion.estado] ?? 0) + 1
    })
    cotizacionStats.value = counts

    const focusProjects = [...proyectoStore.proyectos]
      .filter((proyecto) => !['completado', 'cancelado'].includes(proyecto.estado))
      .sort((a, b) => new Date(b.fecha_creacion).getTime() - new Date(a.fecha_creacion).getTime())
      .slice(0, 3)

    if (focusProjects.length > 0) {
      projectStats.value = await Promise.all(
        focusProjects.map((proyecto) => proyectoStore.fetchEstadisticasProyecto(proyecto.id_proyecto, false))
      )
    } else {
      projectStats.value = []
    }
  } catch {
    // silent dashboard fallback
  } finally {
    loading.value = false
  }
}

let refreshTimer: ReturnType<typeof setInterval> | null = null
const DASHBOARD_REFRESH_MS = 60_000

onMounted(async () => {
  await loadData()
  if (financialCards.value.length > 0) {
    selectedFinancialMetric.value = financialCards.value[0]?.label ?? null
  }
  refreshTimer = setInterval(loadData, DASHBOARD_REFRESH_MS)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<template>
  <div class="space-y-6">
    <section class="rounded-3xl border border-slate-200 bg-[radial-gradient(circle_at_top_left,_rgba(15,23,42,0.06),_transparent_38%),linear-gradient(135deg,#f8fafc_0%,#eef4ff_45%,#f8fafc_100%)] p-6 shadow-sm">
      <div class="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Centro financiero ERP</p>
          <h1 class="mt-2 text-3xl font-bold text-slate-900">
            Bienvenido, {{ auth.user?.nombre_completo ?? auth.user?.username }}
          </h1>
          <p class="mt-2 max-w-2xl text-sm text-slate-600">
            El tablero ahora prioriza facturacion, compras, caja chica, cartera y alertas de cierre para que el seguimiento contable salga de datos reales y no de simulaciones.
          </p>
          <div class="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              class="rounded-full border px-3 py-1 text-xs font-semibold transition"
              :class="dashboardViewMode === 'all' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-300 bg-white text-slate-700 hover:border-slate-400'"
              @click="dashboardViewMode = 'all'"
            >
              Vista completa
            </button>
            <button
              type="button"
              class="rounded-full border px-3 py-1 text-xs font-semibold transition"
              :class="dashboardViewMode === 'finance' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-300 bg-white text-slate-700 hover:border-slate-400'"
              @click="dashboardViewMode = 'finance'"
            >
              Enfoque financiero
            </button>
            <button
              type="button"
              class="rounded-full border px-3 py-1 text-xs font-semibold transition"
              :class="dashboardViewMode === 'operations' ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-300 bg-white text-slate-700 hover:border-slate-400'"
              @click="dashboardViewMode = 'operations'"
            >
              Enfoque operativo
            </button>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div
            v-for="card in operationalCards"
            :key="card.label"
            class="rounded-2xl border border-white/60 bg-white/90 p-4 shadow-sm"
          >
            <div class="flex items-center gap-2">
              <div :class="['rounded-xl p-2', card.bg]">
                <component :is="card.icon" :class="['h-4 w-4', card.tone]" />
              </div>
              <span class="text-xs font-medium text-slate-500">{{ card.label }}</span>
            </div>
            <p class="mt-3 text-2xl font-bold text-slate-900">{{ card.value }}</p>
          </div>
        </div>
      </div>
    </section>

    <section v-if="showFinancialPanels">
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">Cierre del mes</h2>
        <router-link to="/ventas" class="text-sm font-medium text-blue-700 hover:underline">Ir a ventas</router-link>
      </div>
      <div v-if="selectedFinancialCard" class="mb-4 rounded-2xl border border-blue-100 bg-blue-50/70 p-4">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.2em] text-blue-700">Métrica seleccionada</p>
            <p class="mt-1 text-lg font-bold text-slate-900">{{ selectedFinancialCard.label }}</p>
            <p class="mt-1 text-sm text-slate-600">{{ selectedFinancialCard.detail }}</p>
          </div>
          <p class="text-xl font-bold text-blue-700">{{ formatCurrency(selectedFinancialCard.value) }}</p>
        </div>
      </div>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <router-link
          v-for="card in financialCards"
          :key="card.label"
          :to="card.link"
          class="group rounded-2xl border bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
          :class="selectedFinancialMetric === card.label ? 'border-blue-300 ring-2 ring-blue-100' : 'border-slate-200'"
          @mouseenter="selectFinancialMetric(card.label)"
        >
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="text-sm font-medium text-slate-500">{{ card.label }}</p>
              <p class="mt-2 text-3xl font-bold text-slate-900">{{ formatCompactCurrency(card.value) }}</p>
              <p class="mt-1 text-xs text-slate-500">{{ card.detail }}</p>
            </div>
            <div :class="['rounded-2xl p-3', card.bg]">
              <component :is="card.icon" :class="['h-5 w-5', card.tone]" />
            </div>
          </div>
          <div class="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-sm">
            <span class="font-medium text-slate-700">{{ formatCurrency(card.value) }}</span>
            <span class="flex items-center gap-1 text-blue-700 group-hover:gap-2 transition-all">
              Ver detalle
              <ArrowRight class="h-4 w-4" />
            </span>
          </div>
        </router-link>
      </div>
    </section>

    <section v-if="showFinancialPanels || showOperationalPanels" class="grid grid-cols-1 gap-6 xl:grid-cols-[1.6fr_1fr]">
      <Card v-if="showFinancialPanels" title="Tendencia financiera de 6 meses">
        <div class="space-y-4">
          <div class="grid grid-cols-4 gap-3 rounded-2xl bg-slate-50 p-4 text-xs text-slate-600">
            <div>
              <p class="font-semibold text-slate-800">Margen bruto</p>
              <p class="mt-1 text-lg font-bold text-emerald-700">{{ formatCompactCurrency(analytics.margen_bruto_mes) }}</p>
            </div>
            <div>
              <p class="font-semibold text-slate-800">Ingresos caja</p>
              <p class="mt-1 text-lg font-bold text-sky-700">{{ formatCompactCurrency(analytics.caja_ingresos_mes) }}</p>
            </div>
            <div>
              <p class="font-semibold text-slate-800">Egresos caja</p>
              <p class="mt-1 text-lg font-bold text-rose-700">{{ formatCompactCurrency(analytics.caja_egresos_mes) }}</p>
            </div>
            <div>
              <p class="font-semibold text-slate-800">Cotizaciones del mes</p>
              <p class="mt-1 text-lg font-bold text-slate-900">{{ stats.cotizaciones_mes }}</p>
            </div>
          </div>

          <div v-if="analytics.tendencia_mensual.length === 0" class="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">
            Aun no hay suficientes movimientos para construir una tendencia financiera.
          </div>

          <div v-else class="space-y-4">
            <div v-for="month in analytics.tendencia_mensual" :key="month.label" class="rounded-2xl border border-slate-100 p-4">
              <div class="mb-3 flex items-center justify-between">
                <div>
                  <p class="text-sm font-semibold text-slate-900">{{ month.label }}</p>
                  <p class="text-xs text-slate-500">Flujo neto {{ formatCurrency(month.flujo_neto) }}</p>
                </div>
                <Badge :variant="month.flujo_neto >= 0 ? 'success' : 'danger'">
                  {{ month.flujo_neto >= 0 ? 'Sano' : 'Presionado' }}
                </Badge>
              </div>
              <div class="space-y-3">
                <div>
                  <div class="mb-1 flex items-center justify-between text-xs text-slate-500">
                    <span>Ingresos</span>
                    <span>{{ formatCurrency(month.ingresos) }}</span>
                  </div>
                  <div class="h-2 rounded-full bg-slate-100">
                    <div class="h-2 rounded-full bg-emerald-500" :style="{ width: `${(month.ingresos / trendMaxValue) * 100}%` }" />
                  </div>
                </div>
                <div>
                  <div class="mb-1 flex items-center justify-between text-xs text-slate-500">
                    <span>Compras</span>
                    <span>{{ formatCurrency(month.compras) }}</span>
                  </div>
                  <div class="h-2 rounded-full bg-slate-100">
                    <div class="h-2 rounded-full bg-rose-500" :style="{ width: `${(month.compras / trendMaxValue) * 100}%` }" />
                  </div>
                </div>
                <div>
                  <div class="mb-1 flex items-center justify-between text-xs text-slate-500">
                    <span>Egresos caja</span>
                    <span>{{ formatCurrency(month.caja_egresos) }}</span>
                  </div>
                  <div class="h-2 rounded-full bg-slate-100">
                    <div class="h-2 rounded-full bg-amber-500" :style="{ width: `${(month.caja_egresos / trendMaxValue) * 100}%` }" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      <div class="space-y-6">
        <Card v-if="showFinancialPanels" title="Alertas contables">
          <div v-if="analytics.alertas.length === 0" class="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
            No hay alertas financieras activas con los datos actuales.
          </div>
          <div v-else class="space-y-3">
            <div
              v-for="alerta in analytics.alertas"
              :key="`${alerta.title}-${alerta.detail}`"
              :class="['rounded-2xl border p-4', alertClass(alerta.severity)]"
            >
              <div class="flex items-start gap-3">
                <AlertTriangle class="mt-0.5 h-4 w-4 shrink-0" />
                <div class="min-w-0 flex-1">
                  <p class="text-sm font-semibold">{{ alerta.title }}</p>
                  <p class="mt-1 text-sm opacity-90">{{ alerta.detail }}</p>
                  <button
                    v-if="alerta.link"
                    class="mt-3 text-sm font-semibold underline"
                    @click="router.push(alerta.link)"
                  >
                    Revisar modulo
                  </button>
                </div>
              </div>
            </div>
          </div>
        </Card>

        <Card v-if="showOperationalPanels" title="Herramientas contables">
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <button
              v-for="action in quickActions"
              :key="action.path"
              :class="['flex items-center justify-between rounded-2xl px-4 py-3 text-left text-sm font-semibold text-white transition-colors', action.color]"
              @click="router.push(action.path)"
            >
              <span class="flex items-center gap-2">
                <component :is="action.icon" class="h-4 w-4" />
                {{ action.label }}
              </span>
              <ArrowRight class="h-4 w-4" />
            </button>
          </div>
        </Card>

        <Card v-if="showOperationalPanels" title="Proyectos en foco">
          <div v-if="projectStatsInFocus.length === 0" class="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
            Sin proyectos activos para mostrar progreso.
          </div>
          <div v-else class="space-y-3">
            <div
              v-for="project in projectStatsInFocus"
              :key="project.id_proyecto"
              class="rounded-2xl border border-slate-100 p-4"
            >
              <div class="mb-2 flex items-center justify-between gap-3">
                <p class="truncate text-sm font-semibold text-slate-900">{{ project.nombre }}</p>
                <span class="text-xs font-semibold text-slate-600">{{ project.porcentaje_completacion.toFixed(0) }}%</span>
              </div>
              <div class="h-2 rounded-full bg-slate-100">
                <div class="h-2 rounded-full bg-violet-500" :style="{ width: `${Math.min(project.porcentaje_completacion, 100)}%` }" />
              </div>
              <div class="mt-2 flex items-center justify-between text-xs text-slate-500">
                <span>{{ project.tareas_completadas }}/{{ project.total_tareas }} tareas</span>
                <span>{{ project.miembros_asignados }} miembro(s)</span>
              </div>
            </div>
          </div>
        </Card>

        <Card v-if="showOperationalPanels" title="Correlación operativa">
          <div v-if="analytics.correlaciones.length === 0" class="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
            Sin datos suficientes para correlaciones.
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="metric in analytics.correlaciones"
              :key="metric.key"
              :class="['rounded-xl border px-3 py-2', correlationClass(metric.status)]"
            >
              <div class="flex items-center justify-between gap-3">
                <p class="text-sm font-semibold">{{ metric.label }}</p>
                <p class="text-sm font-bold">{{ metric.value.toFixed(2) }}{{ metric.unit }}</p>
              </div>
              <p class="mt-1 text-xs opacity-90">{{ metric.detail }}</p>
            </div>
          </div>
        </Card>
      </div>
    </section>

    <section v-if="showFinancialPanels || showOperationalPanels" class="grid grid-cols-1 gap-6 xl:grid-cols-[1.1fr_0.9fr_0.9fr]">
      <Card v-if="showFinancialPanels" title="Clientes con mayor facturacion">
        <div v-if="analytics.top_clientes.length === 0" class="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">
          Aun no existen facturas suficientes para construir un ranking de clientes.
        </div>
        <div v-else class="space-y-3">
          <div
            v-for="cliente in analytics.top_clientes"
            :key="cliente.id_cliente"
            class="rounded-2xl border border-slate-100 p-4"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-slate-900">{{ cliente.nombre }}</p>
                <p class="mt-1 text-xs text-slate-500">Participacion {{ cliente.participacion_pct.toFixed(2) }}%</p>
              </div>
              <p class="text-sm font-bold text-slate-900">{{ formatCurrency(cliente.total_facturado) }}</p>
            </div>
            <div class="mt-3 h-2 rounded-full bg-slate-100">
              <div class="h-2 rounded-full bg-slate-900" :style="{ width: `${Math.min(cliente.participacion_pct, 100)}%` }" />
            </div>
          </div>
        </div>
      </Card>

      <Card v-if="showFinancialPanels" title="Caja chica por categoria">
        <div v-if="analytics.egresos_por_categoria.length === 0" class="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">
          No hay egresos de caja chica categorizados en el mes.
        </div>
        <div v-else class="space-y-3">
          <div
            v-for="categoria in analytics.egresos_por_categoria"
            :key="categoria.categoria"
            class="rounded-2xl bg-slate-50 p-4"
          >
            <div class="flex items-center justify-between gap-3">
              <p class="text-sm font-semibold text-slate-900">{{ categoria.categoria }}</p>
              <p class="text-sm font-bold text-rose-700">{{ formatCurrency(categoria.total) }}</p>
            </div>
            <p class="mt-1 text-xs text-slate-500">Gasto consolidado del mes en esta categoria.</p>
          </div>
        </div>
      </Card>

      <Card v-if="showFinancialPanels" title="Cartera y vencimientos">
        <div class="space-y-4">
          <div v-if="analytics.cartera_aging.length === 0" class="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">
            No hay cartera pendiente para analizar.
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="bucket in analytics.cartera_aging"
              :key="bucket.bucket"
              class="rounded-xl border border-slate-100 px-3 py-2"
            >
              <div class="flex items-center justify-between text-sm">
                <p class="font-medium text-slate-700">{{ bucket.bucket }}</p>
                <p class="font-semibold text-slate-900">{{ formatCurrency(bucket.total) }}</p>
              </div>
              <p class="mt-0.5 text-xs text-slate-500">{{ bucket.cantidad }} documento(s)</p>
            </div>
          </div>

          <div class="border-t border-slate-100 pt-3">
            <p class="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Próximos vencimientos</p>
            <div v-if="analytics.proximos_vencimientos.length === 0" class="rounded-2xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
              No hay fechas de vencimiento registradas.
            </div>
            <div v-else class="space-y-2">
              <div
                v-for="item in analytics.proximos_vencimientos"
                :key="item.id_cotizacion"
                class="rounded-xl bg-slate-50 p-3"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="truncate text-sm font-semibold text-slate-900">{{ item.numero }} · {{ item.cliente_nombre }}</p>
                    <p class="mt-0.5 text-xs text-slate-500">
                      Vence: {{ item.fecha_vencimiento ?? 'Sin fecha' }}
                    </p>
                  </div>
                  <p class="shrink-0 text-sm font-bold text-slate-900">{{ formatCurrency(item.total) }}</p>
                </div>
                <div class="mt-2 flex items-center justify-between">
                  <span :class="['rounded-full px-2 py-1 text-[11px] font-semibold', dueBadgeClass(item)]">
                    {{ (item.dias_vencido ?? 0) > 0 ? `Vencido ${item.dias_vencido}d` : `Vence en ${item.dias_para_vencer ?? 0}d` }}
                  </span>
                  <button class="text-xs font-semibold text-blue-700 hover:underline" @click="router.push('/ventas')">
                    Gestionar cobro
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      <Card v-if="showOperationalPanels" title="Pipeline y servicio">
        <div class="space-y-4">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Cotizaciones</p>
            <div class="mt-3 space-y-3">
              <div v-for="stage in pipelineStages" :key="stage.estado">
                <div class="mb-1 flex items-center justify-between text-xs">
                  <span class="text-slate-600">{{ stage.label }}</span>
                  <span :class="['font-semibold', stage.textColor]">{{ cotizacionStats[stage.estado] ?? 0 }}</span>
                </div>
                <div class="h-2 rounded-full bg-slate-100">
                  <div
                    :class="['h-2 rounded-full transition-all', stage.color]"
                    :style="{ width: `${((cotizacionStats[stage.estado] ?? 0) / cotizacionTotal) * 100}%` }"
                  />
                </div>
              </div>
            </div>
          </div>

          <div class="border-t border-slate-100 pt-4">
            <div class="mb-3 flex items-center justify-between">
              <p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Tickets recientes</p>
              <router-link to="/taller" class="text-xs font-semibold text-blue-700 hover:underline">Ver todos</router-link>
            </div>

            <div v-if="loading" class="flex justify-center py-8">
              <svg class="h-5 w-5 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <div v-else-if="recentTickets.length === 0" class="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">
              No hay tickets recientes.
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="ticket in recentTickets"
                :key="ticket.id_ticket"
                class="cursor-pointer rounded-2xl border border-slate-100 p-4 transition-colors hover:bg-slate-50"
                @click="router.push('/taller')"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="truncate text-sm font-semibold text-slate-900">{{ ticket.titulo }}</p>
                    <p class="mt-1 text-xs text-slate-500">{{ ticket.numero }}</p>
                  </div>
                  <div class="flex shrink-0 items-center gap-2">
                    <Badge :variant="priorityVariant[ticket.prioridad] ?? 'default'">{{ ticket.prioridad }}</Badge>
                    <Badge :variant="estadoVariant[ticket.estado] ?? 'default'">{{ ticket.estado.replace('_', ' ') }}</Badge>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </section>

    <section v-if="stats.productos_bajo_stock > 0 || stats.tickets_abiertos > 5" class="space-y-2">
      <div v-if="stats.productos_bajo_stock > 0" class="flex items-center gap-3 rounded-2xl border border-red-200 bg-red-50 px-4 py-3">
        <XCircle class="h-4 w-4 shrink-0 text-red-600" />
        <p class="text-sm text-red-800">
          <span class="font-semibold">{{ stats.productos_bajo_stock }} producto(s)</span>
          estan por debajo del stock minimo.
          <router-link to="/compras" class="ml-1 underline">Gestionar inventario</router-link>
        </p>
      </div>
      <div v-if="stats.tickets_abiertos > 5" class="flex items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
        <Clock class="h-4 w-4 shrink-0 text-amber-600" />
        <p class="text-sm text-amber-800">
          <span class="font-semibold">{{ stats.tickets_abiertos }} tickets</span>
          siguen abiertos y requieren coordinacion operativa.
          <router-link to="/taller" class="ml-1 underline">Ver tickets</router-link>
        </p>
      </div>
    </section>
  </div>
</template>
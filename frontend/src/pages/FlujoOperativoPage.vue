<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowRight, Landmark, Receipt, TrendingDown, TrendingUp, Wallet } from 'lucide-vue-next'
import api from '../services/api'
import Card from '../components/ui/Card.vue'
import Badge from '../components/ui/Badge.vue'

interface DashboardTrendPoint {
  label: string
  ingresos: number
  compras: number
  caja_ingresos: number
  caja_egresos: number
  flujo_neto: number
}

interface DashboardAlert {
  severity: 'critical' | 'warning' | 'info'
  title: string
  detail: string
  link?: string | null
}

interface DashboardCorrelationMetric {
  key: string
  label: string
  value: number
  unit: string
  status: 'ok' | 'warning' | 'critical' | string
  detail: string
}

interface DashboardFinanceAnalytics {
  ingresos_facturados_mes: number
  compras_registradas_mes: number
  caja_ingresos_mes: number
  caja_egresos_mes: number
  flujo_neto_mes: number
  alertas: DashboardAlert[]
  tendencia_mensual: DashboardTrendPoint[]
  correlaciones: DashboardCorrelationMetric[]
}

const loading = ref(true)

const analytics = ref<DashboardFinanceAnalytics>({
  ingresos_facturados_mes: 0,
  compras_registradas_mes: 0,
  caja_ingresos_mes: 0,
  caja_egresos_mes: 0,
  flujo_neto_mes: 0,
  alertas: [],
  tendencia_mensual: [],
  correlaciones: [],
})

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

function alertClass(severity: DashboardAlert['severity']): string {
  if (severity === 'critical') return 'border-red-200 bg-red-50 text-red-800'
  if (severity === 'warning') return 'border-amber-200 bg-amber-50 text-amber-800'
  return 'border-sky-200 bg-sky-50 text-sky-800'
}

function correlationClass(status: string): string {
  if (status === 'critical') return 'border-red-200 bg-red-50 text-red-800'
  if (status === 'warning') return 'border-amber-200 bg-amber-50 text-amber-800'
  return 'border-emerald-200 bg-emerald-50 text-emerald-800'
}

const trendMaxValue = computed(() => {
  const values = analytics.value.tendencia_mensual.flatMap((item) => [
    item.ingresos,
    item.compras,
    item.caja_egresos,
    Math.abs(item.flujo_neto),
  ])
  return Math.max(...values, 1)
})

const summaryCards = computed(() => [
  {
    label: 'Ingresos facturados',
    value: analytics.value.ingresos_facturados_mes,
    icon: TrendingUp,
    tone: 'text-emerald-700',
    bg: 'bg-emerald-50',
    link: '/ventas',
  },
  {
    label: 'Compras registradas',
    value: analytics.value.compras_registradas_mes,
    icon: Receipt,
    tone: 'text-rose-700',
    bg: 'bg-rose-50',
    link: '/compras',
  },
  {
    label: 'Movimientos de caja',
    value: analytics.value.caja_ingresos_mes - analytics.value.caja_egresos_mes,
    icon: Wallet,
    tone: analytics.value.caja_ingresos_mes - analytics.value.caja_egresos_mes >= 0 ? 'text-indigo-700' : 'text-red-700',
    bg: analytics.value.caja_ingresos_mes - analytics.value.caja_egresos_mes >= 0 ? 'bg-indigo-50' : 'bg-red-50',
    link: '/caja-chica',
  },
  {
    label: 'Flujo operativo neto',
    value: analytics.value.flujo_neto_mes,
    icon: analytics.value.flujo_neto_mes >= 0 ? Landmark : TrendingDown,
    tone: analytics.value.flujo_neto_mes >= 0 ? 'text-sky-700' : 'text-red-700',
    bg: analytics.value.flujo_neto_mes >= 0 ? 'bg-sky-50' : 'bg-red-50',
    link: '/dashboard',
  },
])

async function loadData(): Promise<void> {
  try {
    const res = await api.get<DashboardFinanceAnalytics>('/api/v1/dashboard/analytics')
    analytics.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadData()
})
</script>

<template>
  <div class="space-y-6">
    <section class="rounded-3xl border border-slate-200 bg-[radial-gradient(circle_at_top_left,_rgba(15,23,42,0.06),_transparent_38%),linear-gradient(135deg,#f8fafc_0%,#eef4ff_45%,#f8fafc_100%)] p-6 shadow-sm">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Vista operativa mensual</p>
          <h1 class="mt-2 text-3xl font-bold text-slate-900">Flujo Operativo</h1>
          <p class="mt-2 max-w-2xl text-sm text-slate-600">
            Consolidado de ingresos, compras y caja chica para monitorear si la operación mensual está generando caja real.
          </p>
        </div>
        <router-link to="/" class="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
          Volver al dashboard
          <ArrowRight class="h-4 w-4" />
        </router-link>
      </div>
    </section>

    <section class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <router-link
        v-for="card in summaryCards"
        :key="card.label"
        :to="card.link"
        class="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-sm font-medium text-slate-500">{{ card.label }}</p>
            <p class="mt-2 text-3xl font-bold text-slate-900">{{ formatCompactCurrency(card.value) }}</p>
          </div>
          <div :class="['rounded-2xl p-3', card.bg]">
            <component :is="card.icon" :class="['h-5 w-5', card.tone]" />
          </div>
        </div>
        <div class="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-sm">
          <span class="font-medium text-slate-700">{{ formatCurrency(card.value) }}</span>
          <span class="flex items-center gap-1 text-blue-700 group-hover:gap-2 transition-all">
            Ver módulo
            <ArrowRight class="h-4 w-4" />
          </span>
        </div>
      </router-link>
    </section>

    <section class="grid grid-cols-1 gap-6 xl:grid-cols-[1.6fr_1fr]">
      <Card title="Evolución de flujo (6 meses)">
        <div v-if="loading" class="flex justify-center py-8">
          <svg class="h-5 w-5 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
        <div v-else-if="analytics.tendencia_mensual.length === 0" class="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">
          Aún no hay datos para construir la tendencia de flujo.
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
      </Card>

      <div class="space-y-6">
        <Card title="Alertas de flujo">
          <div v-if="analytics.alertas.length === 0" class="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
            No hay alertas activas con los datos actuales.
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="alerta in analytics.alertas"
              :key="`${alerta.title}-${alerta.detail}`"
              :class="['rounded-xl border px-3 py-2', alertClass(alerta.severity)]"
            >
              <p class="text-sm font-semibold">{{ alerta.title }}</p>
              <p class="mt-1 text-xs opacity-90">{{ alerta.detail }}</p>
            </div>
          </div>
        </Card>

        <Card title="Correlación operativa">
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
  </div>
</template>
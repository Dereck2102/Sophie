import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'

export interface DashboardStats {
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

export interface DashboardTrendPoint {
  label: string
  ingresos: number
  compras: number
  caja_ingresos: number
  caja_egresos: number
  flujo_neto: number
}

export interface DashboardTopClient {
  id_cliente: number
  nombre: string
  total_facturado: number
  participacion_pct: number
}

export interface DashboardExpenseCategory {
  categoria: string
  total: number
}

export interface DashboardReceivableBucket {
  bucket: string
  total: number
  cantidad: number
}

export interface DashboardReceivableDueItem {
  id_cotizacion: number
  numero: string
  id_cliente: number
  cliente_nombre: string
  estado: string
  total: number
  fecha_vencimiento?: string | null
  dias_para_vencer?: number | null
  dias_vencido?: number | null
}

export interface DashboardAlert {
  severity: 'critical' | 'warning' | 'info'
  title: string
  detail: string
  link?: string | null
}

export interface DashboardCorrelationMetric {
  key: string
  label: string
  value: number
  unit: string
  status: 'ok' | 'warning' | 'critical' | string
  detail: string
}

export interface DashboardFinanceAnalytics {
  ingresos_facturados_mes: number
  compras_registradas_mes: number
  caja_ingresos_mes: number
  caja_egresos_mes: number
  flujo_neto_mes: number
  cuentas_por_cobrar: number
  ordenes_pendientes_monto: number
  margen_bruto_mes: number
  caja_chica_balance: number
  top_clientes: DashboardTopClient[]
  egresos_por_categoria: DashboardExpenseCategory[]
  cartera_aging: DashboardReceivableBucket[]
  proximos_vencimientos: DashboardReceivableDueItem[]
  tendencia_mensual: DashboardTrendPoint[]
  alertas: DashboardAlert[]
  correlaciones: DashboardCorrelationMetric[]
}

const STATS_TTL_MS = 60_000
const ANALYTICS_TTL_MS = 60_000

export const useDashboardStore = defineStore('dashboard', () => {
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

  const analytics = ref<DashboardFinanceAnalytics>({
    ingresos_facturados_mes: 0,
    compras_registradas_mes: 0,
    caja_ingresos_mes: 0,
    caja_egresos_mes: 0,
    flujo_neto_mes: 0,
    cuentas_por_cobrar: 0,
    ordenes_pendientes_monto: 0,
    margen_bruto_mes: 0,
    caja_chica_balance: 0,
    top_clientes: [],
    egresos_por_categoria: [],
    cartera_aging: [],
    proximos_vencimientos: [],
    tendencia_mensual: [],
    alertas: [],
    correlaciones: [],
  })

  const loadingStats = ref(false)
  const loadingAnalytics = ref(false)
  const lastStatsLoadedAt = ref<number | null>(null)
  const lastAnalyticsLoadedAt = ref<number | null>(null)
  const cacheMetrics = ref({
    statsHits: 0,
    statsMisses: 0,
    statsInFlightReuses: 0,
    statsNetworkLoads: 0,
    analyticsHits: 0,
    analyticsMisses: 0,
    analyticsInFlightReuses: 0,
    analyticsNetworkLoads: 0,
  })

  let statsRequest: Promise<void> | null = null
  let analyticsRequest: Promise<void> | null = null

  async function fetchStats(force = false): Promise<void> {
    if (!force && lastStatsLoadedAt.value && Date.now() - lastStatsLoadedAt.value < STATS_TTL_MS) {
      cacheMetrics.value.statsHits += 1
      return
    }
    cacheMetrics.value.statsMisses += 1
    if (statsRequest) {
      cacheMetrics.value.statsInFlightReuses += 1
      return statsRequest
    }

    loadingStats.value = true
    cacheMetrics.value.statsNetworkLoads += 1
    statsRequest = (async () => {
      try {
        const { data } = await api.get<DashboardStats>('/api/v1/dashboard/stats')
        stats.value = data
        lastStatsLoadedAt.value = Date.now()
      } finally {
        loadingStats.value = false
        statsRequest = null
      }
    })()

    return statsRequest
  }

  async function fetchAnalytics(force = false): Promise<void> {
    if (!force && lastAnalyticsLoadedAt.value && Date.now() - lastAnalyticsLoadedAt.value < ANALYTICS_TTL_MS) {
      cacheMetrics.value.analyticsHits += 1
      return
    }
    cacheMetrics.value.analyticsMisses += 1
    if (analyticsRequest) {
      cacheMetrics.value.analyticsInFlightReuses += 1
      return analyticsRequest
    }

    loadingAnalytics.value = true
    cacheMetrics.value.analyticsNetworkLoads += 1
    analyticsRequest = (async () => {
      try {
        const { data } = await api.get<DashboardFinanceAnalytics>('/api/v1/dashboard/analytics')
        analytics.value = data
        lastAnalyticsLoadedAt.value = Date.now()
      } finally {
        loadingAnalytics.value = false
        analyticsRequest = null
      }
    })()

    return analyticsRequest
  }

  async function fetchAll(force = false): Promise<void> {
    await Promise.all([fetchStats(force), fetchAnalytics(force)])
  }

  function invalidateCache(options?: { stats?: boolean; analytics?: boolean }): void {
    const invalidateStats = options?.stats ?? true
    const invalidateAnalytics = options?.analytics ?? true

    if (invalidateStats) lastStatsLoadedAt.value = null
    if (invalidateAnalytics) lastAnalyticsLoadedAt.value = null
  }

  function resetCacheMetrics(): void {
    cacheMetrics.value = {
      statsHits: 0,
      statsMisses: 0,
      statsInFlightReuses: 0,
      statsNetworkLoads: 0,
      analyticsHits: 0,
      analyticsMisses: 0,
      analyticsInFlightReuses: 0,
      analyticsNetworkLoads: 0,
    }
  }

  return {
    stats,
    analytics,
    loadingStats,
    loadingAnalytics,
    cacheMetrics,
    lastStatsLoadedAt,
    lastAnalyticsLoadedAt,
    fetchStats,
    fetchAnalytics,
    fetchAll,
    invalidateCache,
    resetCacheMetrics,
  }
})

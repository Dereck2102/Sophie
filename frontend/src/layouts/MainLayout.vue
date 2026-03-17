<script setup lang="ts">
import { onMounted, watch } from 'vue'
import SidebarNav from '../components/layout/SidebarNav.vue'
import TopBar from '../components/layout/TopBar.vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { useDashboardStore } from '../stores/dashboard'
import { useNotificationStore } from '../stores/notifications'
import { useTicketStore } from '../stores/tickets'
import { useVentasStore } from '../stores/ventas'
import { useProyectoStore } from '../stores/proyectos'
import { useBovedaStore } from '../stores/boveda'

const route = useRoute()
const { t } = useI18n()
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const notificationStore = useNotificationStore()
const ticketStore = useTicketStore()
const ventasStore = useVentasStore()
const proyectoStore = useProyectoStore()
const bovedaStore = useBovedaStore()

function getCacheMetricsSnapshot() {
  return {
    dashboard: { ...dashboardStore.cacheMetrics },
    tickets: { ...ticketStore.cacheMetrics },
    ventas: { ...ventasStore.cacheMetrics },
    proyectos: { ...proyectoStore.cacheMetrics },
    boveda: { ...bovedaStore.cacheMetrics },
  }
}

function setupDevCacheMetricsConsole(): void {
  if (!import.meta.env.DEV) return

  ;(window as { __SOPHIE_CACHE_METRICS__?: () => unknown }).__SOPHIE_CACHE_METRICS__ = () => getCacheMetricsSnapshot()
  ;(window as { __SOPHIE_PRINT_CACHE_METRICS__?: () => void }).__SOPHIE_PRINT_CACHE_METRICS__ = () => {
    console.table(getCacheMetricsSnapshot())
  }
  ;(window as { __SOPHIE_RESET_CACHE_METRICS__?: () => unknown }).__SOPHIE_RESET_CACHE_METRICS__ = () => {
    dashboardStore.resetCacheMetrics()
    ticketStore.resetCacheMetrics()
    ventasStore.resetCacheMetrics()
    proyectoStore.resetCacheMetrics()
    bovedaStore.resetCacheMetrics()
    return getCacheMetricsSnapshot()
  }
  console.info('SOPHIE cache metrics helpers: __SOPHIE_CACHE_METRICS__(), __SOPHIE_PRINT_CACHE_METRICS__(), __SOPHIE_RESET_CACHE_METRICS__()')
}

function refreshDashboardIfStale(): void {
  const hasDashboard = authStore.user?.vistas.includes('*') || authStore.user?.vistas.includes('dashboard')
  if (!hasDashboard) return
  const statsStale = !dashboardStore.lastStatsLoadedAt
  const analyticsStale = !dashboardStore.lastAnalyticsLoadedAt

  if (statsStale && analyticsStale) {
    void dashboardStore.fetchAll(false).catch(() => {
      // non-blocking refresh
    })
    return
  }

  if (statsStale) {
    void dashboardStore.fetchStats(false).catch(() => {
      // non-blocking refresh
    })
  }

  if (analyticsStale) {
    void dashboardStore.fetchAnalytics(false).catch(() => {
      // non-blocking refresh
    })
  }
}

const pageTitle = () => {
  const path = route.path
  const titles: Record<string, string> = {
    '/': t('nav.dashboard'),
    '/crm': t('nav.crm'),
    '/ventas': t('nav.ventas'),
    '/compras': t('nav.compras'),
    '/taller': t('nav.taller'),
    '/proyectos': t('nav.proyectos'),
    '/boveda': t('nav.boveda'),
    '/usuarios': t('nav.usuarios'),
    '/configuracion': t('nav.configuracion'),
    '/perfil': t('nav.perfil'),
  }
  if (titles[path]) return titles[path]
  if (path.startsWith('/crm/')) return 'SOPHIE'
  return 'SOPHIE'
}

onMounted(async () => {
  setupDevCacheMetricsConsole()
  try {
    const hasDashboard = authStore.user?.vistas.includes('*') || authStore.user?.vistas.includes('dashboard')
    const preloads: Promise<unknown>[] = [notificationStore.fetchNotifications(false)]
    if (hasDashboard) preloads.push(dashboardStore.fetchAll(false))
    await Promise.all(preloads)
  } catch {
    // non-blocking preload
  }
})

watch(
  () => route.fullPath,
  () => {
    refreshDashboardIfStale()
  }
)
</script>

<template>
  <div class="flex h-screen bg-gray-50 dark:bg-gray-950">
    <SidebarNav />
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <TopBar :title="pageTitle()" />
      <main class="flex-1 overflow-y-auto p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>

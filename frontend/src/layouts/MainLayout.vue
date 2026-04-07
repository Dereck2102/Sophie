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

const route = useRoute()
const { t } = useI18n()
const authStore = useAuthStore()
const dashboardStore = useDashboardStore()
const notificationStore = useNotificationStore()
const ticketStore = useTicketStore()
const ventasStore = useVentasStore()
const proyectoStore = useProyectoStore()

function getCacheMetricsSnapshot() {
  return {
    dashboard: { ...dashboardStore.cacheMetrics },
    tickets: { ...ticketStore.cacheMetrics },
    ventas: { ...ventasStore.cacheMetrics },
    proyectos: { ...proyectoStore.cacheMetrics },
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
    '/global/dashboard': t('nav.globalDashboard'),
    '/global/companies': t('nav.globalCompanies'),
    '/global/users': t('nav.globalUsers'),
    '/global/tickets': t('nav.globalTickets'),
    '/ventas': t('nav.ventas'),
    '/compras': t('nav.compras'),
    '/taller': t('nav.taller'),
    '/proyectos': t('nav.proyectos'),
    '/empresas': t('nav.empresas'),
    '/usuarios': t('nav.usuarios'),
    '/configuracion': t('nav.configuracion'),
    '/perfil': t('nav.perfil'),
  }
  if (titles[path]) return titles[path]
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
  <div class="flex min-h-screen bg-transparent text-slate-900 dark:text-slate-100">
    <div class="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div class="absolute -left-24 top-10 h-72 w-72 rounded-full bg-sky-400/15 blur-3xl"></div>
      <div class="absolute right-0 top-40 h-80 w-80 rounded-full bg-cyan-500/10 blur-3xl"></div>
      <div class="absolute bottom-0 left-1/3 h-96 w-96 rounded-full bg-indigo-400/10 blur-3xl"></div>
    </div>
    <SidebarNav />
    <div class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <TopBar :title="pageTitle()" />
      <main class="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
        <RouterView />
      </main>
    </div>
  </div>
</template>

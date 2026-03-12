import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import api from '../services/api'
import { useAuthStore } from './auth'
import type { Usuario } from '../types'

interface DashboardStats {
  total_clientes: number
  cotizaciones_mes: number
  tickets_abiertos: number
  productos_bajo_stock: number
  revenue_mes: number
  proyectos_activos: number
}

export interface AppNotification {
  id: string
  title: string
  description: string
  route: string
  severity: 'info' | 'warning' | 'critical'
}

export const useNotificationStore = defineStore('notifications', () => {
  const items = ref<AppNotification[]>([])
  const loading = ref(false)
  const lastLoadedAt = ref<number | null>(null)

  const unreadCount = computed(() => items.value.length)

  async function fetchNotifications(force = false): Promise<void> {
    if (loading.value) return
    if (!force && lastLoadedAt.value && Date.now() - lastLoadedAt.value < 60_000) return

    loading.value = true
    try {
      const auth = useAuthStore()
      const requests: Promise<unknown>[] = [
        api.get<DashboardStats>('/api/v1/dashboard/stats'),
      ]

      const isAdmin = auth.user?.rol === 'admin'
      if (isAdmin) {
        requests.push(api.get<Usuario[]>('/api/v1/usuarios/', { params: { limit: 200 } }))
      }

      const [statsResponse, adminUsersResponse] = await Promise.all(requests)
      const notifications: AppNotification[] = []
      const stats = (statsResponse as { data: DashboardStats }).data

      if (!auth.user?.mfa_habilitado) {
        notifications.push({
          id: 'mfa-disabled',
          title: 'Tu cuenta aún no tiene MFA',
          description: 'Activa autenticación de dos factores para proteger accesos administrativos.',
          route: '/perfil',
          severity: 'warning',
        })
      }

      if (stats.productos_bajo_stock > 0) {
        notifications.push({
          id: 'low-stock',
          title: 'Inventario con stock crítico',
          description: `${stats.productos_bajo_stock} producto(s) están por debajo del mínimo.`,
          route: '/compras',
          severity: 'critical',
        })
      }

      if (stats.tickets_abiertos > 0) {
        notifications.push({
          id: 'open-tickets',
          title: 'Tickets pendientes de atención',
          description: `${stats.tickets_abiertos} ticket(s) siguen abiertos o en progreso.`,
          route: '/taller',
          severity: 'info',
        })
      }

      if (stats.cotizaciones_mes > 0) {
        notifications.push({
          id: 'quotes-month',
          title: 'Actividad comercial del mes',
          description: `${stats.cotizaciones_mes} cotización(es) creadas este mes.`,
          route: '/ventas',
          severity: 'info',
        })
      }

      if (isAdmin && adminUsersResponse) {
        const users = (adminUsersResponse as { data: Usuario[] }).data
        const inactiveUsers = users.filter((user) => !user.activo).length
        if (inactiveUsers > 0) {
          notifications.push({
            id: 'inactive-users',
            title: 'Usuarios desactivados por revisar',
            description: `${inactiveUsers} cuenta(s) están inactivas y pueden requerir gestión administrativa.`,
            route: '/usuarios',
            severity: 'warning',
          })
        }
      }

      items.value = notifications
      lastLoadedAt.value = Date.now()
    } finally {
      loading.value = false
    }
  }

  return { items, loading, unreadCount, fetchNotifications }
})
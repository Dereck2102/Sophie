import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import type { Usuario } from '../types'

// Maps each effective view key to its named route
const VIEW_ROUTE_MAP: Record<string, string> = {
  dashboard: 'Dashboard',
  taller: 'Taller',
  proyectos: 'Proyectos',
  crm: 'CRM',
  ventas: 'Ventas',
  compras: 'Compras',
  caja_chica: 'CajaChica',
  boveda: 'Boveda',
  usuarios: 'Usuarios',
  configuracion: 'Configuracion',
  auditoria: 'Auditoria',
}

// Priority order for determining the home route when dashboard is unavailable
const VIEW_PRIORITY = [
  'dashboard', 'taller', 'proyectos', 'crm', 'ventas',
  'compras', 'caja_chica', 'boveda', 'auditoria',
]

// Role-specific landing page priority: technical roles land on their primary domain
const ROLE_VIEW_PRIORITY: Partial<Record<string, string[]>> = {
  tecnico:            ['taller'],
  tecnico_taller:     ['taller'],
  desarrollador:      ['proyectos', 'taller', 'boveda'],
  agente_soporte_l1:  ['crm', 'taller'],
  agente_soporte_l2:  ['crm', 'proyectos', 'taller'],
  jefe_taller:        ['taller', 'dashboard', 'crm'],
  jefe_tecnologias:   ['proyectos', 'dashboard', 'taller'],
}

function getHomeRoute(user: Usuario | null): { name: string } {
  if (!user) return { name: 'Login' }
  const views = user.vistas ?? []
  if (views.includes('*')) return { name: 'Dashboard' }

  // Role-specific landing view takes priority
  const rolePriority = ROLE_VIEW_PRIORITY[user.rol] ?? []
  for (const v of rolePriority) {
    if (views.includes(v) && VIEW_ROUTE_MAP[v]) return { name: VIEW_ROUTE_MAP[v] }
  }

  // Generic fallback priority
  for (const v of VIEW_PRIORITY) {
    if (views.includes(v) && VIEW_ROUTE_MAP[v]) return { name: VIEW_ROUTE_MAP[v] }
  }
  return { name: 'Perfil' }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/LoginPage.vue'),
    meta: { public: true },
  },
  {
    path: '/orden/:token',
    name: 'OrdenTrabajo',
    component: () => import('../pages/OrdenTrabajoPage.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Dashboard', component: () => import('../pages/DashboardPage.vue'), meta: { requiredView: 'dashboard' } },
      { path: 'flujo-operativo', name: 'FlujoOperativo', component: () => import('../pages/FlujoOperativoPage.vue'), meta: { requiredView: 'dashboard' } },
      { path: 'crm', name: 'CRM', component: () => import('../pages/CrmPage.vue'), meta: { requiredView: 'crm' } },
      { path: 'crm/:id', name: 'ClienteDetail', component: () => import('../pages/ClienteDetailPage.vue'), meta: { requiredView: 'crm' } },
      { path: 'ventas', name: 'Ventas', component: () => import('../pages/VentasPage.vue'), meta: { requiredView: 'ventas' } },
      { path: 'compras', name: 'Compras', component: () => import('../pages/ComprasPage.vue'), meta: { requiredView: 'compras' } },
      { path: 'caja-chica', name: 'CajaChica', component: () => import('../pages/CajaChicaPage.vue'), meta: { requiredView: 'caja_chica' } },
      { path: 'taller', name: 'Taller', component: () => import('../pages/TallerPage.vue'), meta: { requiredView: 'taller' } },
      { path: 'proyectos', name: 'Proyectos', component: () => import('../pages/ProyectosPage.vue'), meta: { requiredView: 'proyectos' } },
      { path: 'boveda', name: 'Boveda', component: () => import('../pages/BovedaPage.vue'), meta: { requiredView: 'boveda' } },
      { path: 'usuarios', name: 'Usuarios', component: () => import('../pages/UsuariosPage.vue'), meta: { requiredView: 'usuarios' } },
      { path: 'configuracion', name: 'Configuracion', component: () => import('../pages/ConfigPage.vue'), meta: { requiredView: 'configuracion' } },
      { path: 'auditoria', name: 'Auditoria', component: () => import('../pages/AuditoriaPage.vue'), meta: { requiredView: 'auditoria' } },
      { path: 'perfil', name: 'Perfil', component: () => import('../pages/PerfilPage.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()
  const requiredView = (to.meta?.requiredView as string | undefined) ?? null
  const userViews = auth.user?.vistas ?? []
  const canAccess = !requiredView || userViews.includes('*') || userViews.includes(requiredView)

  if (to.meta.requiresAuth && !auth.accessToken) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && auth.accessToken && auth.user) {
    next(getHomeRoute(auth.user))
  } else if (requiredView && auth.user && !canAccess) {
    next(getHomeRoute(auth.user))
  } else {
    next()
  }
})

export default router

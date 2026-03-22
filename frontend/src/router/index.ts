import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import type { EnterpriseModuleCode } from '../stores/subscription'
import { useSubscriptionStore } from '../stores/subscription'
import type { Usuario } from '../types'

const ERP_ONLY_MODE = true
const ERP_ONLY_DISABLED_VIEWS = new Set(['crm'])

// Maps each effective view key to its named route
const VIEW_ROUTE_MAP: Record<string, string> = {
  dashboard: 'Dashboard',
  global_dashboard: 'GlobalDashboard',
  taller: 'Taller',
  proyectos: 'Proyectos',
  ventas: 'Ventas',
  compras: 'Compras',
  caja_chica: 'CajaChica',
  empresas: 'Empresas',
  usuarios: 'Usuarios',
  configuracion: 'Configuracion',
  auditoria: 'Auditoria',
}

// Priority order for determining the home route when dashboard is unavailable
const VIEW_PRIORITY = [
  'dashboard', 'taller', 'proyectos', 'ventas',
  'compras', 'caja_chica', 'empresas', 'auditoria',
]

// Role-specific landing page priority: technical roles land on their primary domain
const ROLE_VIEW_PRIORITY: Partial<Record<string, string[]>> = {
  tecnico:            ['taller'],
  tecnico_taller:     ['taller'],
  desarrollador:      ['proyectos', 'taller', 'empresas'],
  agente_soporte_l1:  ['taller'],
  agente_soporte_l2:  ['proyectos', 'taller'],
  jefe_taller:        ['taller', 'dashboard'],
  jefe_tecnologias:   ['proyectos', 'dashboard', 'taller'],
}

function getHomeRoute(user: Usuario | null): { name: string } {
  if (!user) return { name: 'Login' }
  if (user.rol === 'superadmin') return { name: 'GlobalDashboard' }
  const subscription = useSubscriptionStore()
  const views = (user.vistas ?? []).filter((view) => !(ERP_ONLY_MODE && ERP_ONLY_DISABLED_VIEWS.has(view)))
  if (views.includes('*') && subscription.hasModuleForView('dashboard')) return { name: 'Dashboard' }

  // Role-specific landing view takes priority
  const rolePriority = ROLE_VIEW_PRIORITY[user.rol] ?? []
  for (const v of rolePriority) {
    if (views.includes(v) && VIEW_ROUTE_MAP[v] && subscription.hasModuleForView(v)) return { name: VIEW_ROUTE_MAP[v] }
  }

  // Generic fallback priority
  for (const v of VIEW_PRIORITY) {
    if (views.includes(v) && VIEW_ROUTE_MAP[v] && subscription.hasModuleForView(v)) return { name: VIEW_ROUTE_MAP[v] }
  }
  return { name: 'Perfil' }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/public',
    name: 'PublicLanding',
    component: () => import('../pages/PublicLandingPage.vue'),
    meta: { public: true },
  },
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
      { path: '', name: 'Dashboard', component: () => import('../pages/DashboardPage.vue'), meta: { requiredView: 'dashboard', requiredModule: 'E2' } },
      { path: 'global/dashboard', name: 'GlobalDashboard', component: () => import('../pages/GlobalDashboardPage.vue'), meta: { requiresSuperadmin: true } },
      { path: 'global/companies', name: 'GlobalCompanies', component: () => import('../pages/GlobalCompaniesPage.vue'), meta: { requiresSuperadmin: true } },
      { path: 'global/users', name: 'GlobalUsers', component: () => import('../pages/GlobalUsersPage.vue'), meta: { requiresSuperadmin: true } },
      { path: 'global/configuration', name: 'GlobalConfiguration', component: () => import('../pages/ConfigPage.vue'), meta: { requiresSuperadmin: true } },
      { path: 'boveda', redirect: '/empresas' },
      { path: 'flujo-operativo', name: 'FlujoOperativo', component: () => import('../pages/FlujoOperativoPage.vue'), meta: { requiredView: 'dashboard', requiredModule: 'E7' } },
      { path: 'ventas', name: 'Ventas', component: () => import('../pages/VentasPage.vue'), meta: { requiredView: 'ventas', requiredModule: 'E4' } },
      { path: 'compras', name: 'Compras', component: () => import('../pages/ComprasPage.vue'), meta: { requiredView: 'compras', requiredModule: 'E5' } },
      { path: 'caja-chica', name: 'CajaChica', component: () => import('../pages/CajaChicaPage.vue'), meta: { requiredView: 'caja_chica', requiredModule: 'E3' } },
      { path: 'taller', name: 'Taller', component: () => import('../pages/TallerPage.vue'), meta: { requiredView: 'taller', requiredModule: 'E8' } },
      { path: 'proyectos', name: 'Proyectos', component: () => import('../pages/ProyectosPage.vue'), meta: { requiredView: 'proyectos', requiredModule: 'E6' } },
      { path: 'empresas', name: 'Empresas', component: () => import('../pages/EmpresasPage.vue'), meta: { requiredView: 'empresas', requiredModule: 'E1' } },
      { path: 'usuarios', name: 'Usuarios', component: () => import('../pages/UsuariosPage.vue'), meta: { requiredView: 'usuarios', requiredModule: 'E1' } },
      { path: 'configuracion', name: 'Configuracion', component: () => import('../pages/ConfigPage.vue'), meta: { requiredView: 'configuracion', requiredModule: 'E1' } },
      { path: 'auditoria', name: 'Auditoria', component: () => import('../pages/AuditoriaPage.vue'), meta: { requiredView: 'auditoria', requiredModule: 'E2' } },
      { path: 'perfil', name: 'Perfil', component: () => import('../pages/PerfilPage.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()
  const subscription = useSubscriptionStore()

  if (auth.accessToken && !auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      // handled by auth store via logout fallback
    }
  }

  const requiredView = (to.meta?.requiredView as string | undefined) ?? null
  const requiredModule = (to.meta?.requiredModule as string | undefined) ?? null
  const requiresSuperadmin = Boolean(to.meta?.requiresSuperadmin)
  const isSuperadmin = auth.user?.rol === 'superadmin'
  const isGlobalRoute = to.path.startsWith('/global/')
  const isSuperadminAllowedRoute = isGlobalRoute || to.name === 'Perfil' || to.name === 'Login' || Boolean(to.meta?.public)
  const userViews = auth.user?.vistas ?? []
  const canAccess = !requiredView || userViews.includes('*') || userViews.includes(requiredView)
  const isDisabledInErpOnly = ERP_ONLY_MODE && Boolean(to.meta?.disabledInErpOnly)

  if (auth.accessToken && auth.user && auth.user.rol !== 'superadmin' && !subscription.initialized) {
    try {
      await subscription.bootstrapForCurrentUser(auth.user)
    } catch {
      // fail-open to avoid blocking navigation on transient API issues
    }
  }

  const canAccessModule = !requiredModule || auth.user?.rol === 'superadmin' || subscription.hasModule(requiredModule as EnterpriseModuleCode)

  if (to.meta.requiresAuth && !auth.accessToken) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (isSuperadmin && !isSuperadminAllowedRoute) {
    next({ name: 'GlobalDashboard' })
  } else if (requiresSuperadmin && auth.user?.rol !== 'superadmin') {
    next(getHomeRoute(auth.user))
  } else if (requiredModule && auth.user && !canAccessModule) {
    next(getHomeRoute(auth.user))
  } else if (isDisabledInErpOnly && auth.user) {
    next(getHomeRoute(auth.user))
  } else if (to.name === 'Login' && auth.accessToken && auth.user) {
    next(getHomeRoute(auth.user))
  } else if (requiredView && auth.user && !canAccess) {
    next(getHomeRoute(auth.user))
  } else {
    next()
  }
})

export default router

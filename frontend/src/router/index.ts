import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'

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
      { path: '', name: 'Dashboard', component: () => import('../pages/DashboardPage.vue') },
      { path: 'flujo-operativo', name: 'FlujoOperativo', component: () => import('../pages/FlujoOperativoPage.vue'), meta: { requiredView: 'dashboard' } },
      { path: 'crm', name: 'CRM', component: () => import('../pages/CrmPage.vue'), meta: { requiredView: 'crm' } },
      { path: 'crm/:id', name: 'ClienteDetail', component: () => import('../pages/ClienteDetailPage.vue') },
      { path: 'ventas', name: 'Ventas', component: () => import('../pages/VentasPage.vue'), meta: { requiredView: 'ventas' } },
      { path: 'compras', name: 'Compras', component: () => import('../pages/ComprasPage.vue'), meta: { requiredView: 'compras' } },
      { path: 'caja-chica', name: 'CajaChica', component: () => import('../pages/CajaChicaPage.vue') },
      { path: 'taller', name: 'Taller', component: () => import('../pages/TallerPage.vue'), meta: { requiredView: 'taller' } },
      { path: 'proyectos', name: 'Proyectos', component: () => import('../pages/ProyectosPage.vue'), meta: { requiredView: 'proyectos' } },
      { path: 'boveda', name: 'Boveda', component: () => import('../pages/BovedaPage.vue'), meta: { requiredView: 'boveda' } },
      { path: 'usuarios', name: 'Usuarios', component: () => import('../pages/UsuariosPage.vue'), meta: { superadminOnly: true } },
      { path: 'configuracion', name: 'Configuracion', component: () => import('../pages/ConfigPage.vue'), meta: { superadminOnly: true } },
      { path: 'auditoria', name: 'Auditoria', component: () => import('../pages/AuditoriaPage.vue'), meta: { superadminOnly: true } },
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
  const isSuperadmin = auth.user?.rol === 'superadmin'
  const canAccessView = !requiredView || isSuperadmin || userViews.includes('*') || userViews.includes(requiredView)
  if (to.meta.requiresAuth && !auth.accessToken) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && auth.accessToken) {
    next({ name: 'Dashboard' })
  } else if (to.meta.superadminOnly && auth.user && auth.user.rol !== 'superadmin') {
    next({ name: 'Dashboard' })
  } else if (requiredView && auth.user && !canAccessView) {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router

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
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Dashboard', component: () => import('../pages/DashboardPage.vue') },
      { path: 'crm', name: 'CRM', component: () => import('../pages/CrmPage.vue') },
      { path: 'crm/:id', name: 'ClienteDetail', component: () => import('../pages/ClienteDetailPage.vue') },
      { path: 'ventas', name: 'Ventas', component: () => import('../pages/VentasPage.vue') },
      { path: 'compras', name: 'Compras', component: () => import('../pages/ComprasPage.vue') },
      { path: 'taller', name: 'Taller', component: () => import('../pages/TallerPage.vue') },
      { path: 'proyectos', name: 'Proyectos', component: () => import('../pages/ProyectosPage.vue') },
      { path: 'boveda', name: 'Boveda', component: () => import('../pages/BovedaPage.vue') },
      { path: 'usuarios', name: 'Usuarios', component: () => import('../pages/UsuariosPage.vue'), meta: { adminOnly: true } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.accessToken) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && auth.accessToken) {
    next({ name: 'Dashboard' })
  } else if (to.meta.adminOnly && auth.user && auth.user.rol !== 'admin') {
    next({ name: 'Dashboard' })
  } else {
    next()
  }
})

export default router

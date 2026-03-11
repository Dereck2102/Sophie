<script setup lang="ts">
import SidebarNav from '../components/layout/SidebarNav.vue'
import TopBar from '../components/layout/TopBar.vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/crm': 'CRM — Clientes',
  '/ventas': 'Ventas & Cotizaciones',
  '/compras': 'Compras & Inventario',
  '/taller': 'Taller de Reparaciones',
  '/proyectos': 'Proyectos & Asesoría',
  '/boveda': 'Bóveda de Credenciales',
  '/usuarios': 'Gestión de Usuarios',
}

const pageTitle = () => {
  const path = route.path
  if (pageTitles[path]) return pageTitles[path]
  if (path.startsWith('/crm/')) return 'Detalle de Cliente'
  return 'SOPHIE'
}
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <SidebarNav />
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <TopBar :title="pageTitle()" />
      <main class="flex-1 overflow-y-auto p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>

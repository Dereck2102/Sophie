<script setup lang="ts">
import SidebarNav from '../components/layout/SidebarNav.vue'
import TopBar from '../components/layout/TopBar.vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

const route = useRoute()
const { t } = useI18n()

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

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  LayoutDashboard,
  Landmark,
  Users,
  ShoppingCart,
  Package,
  Wallet,
  Wrench,
  Code2,
  Lock,
  UserCog,
  ClipboardList,
  ChevronLeft,
  ChevronRight,
  Settings,
} from 'lucide-vue-next'
import { useAuthStore } from '../../stores/auth'
import { useI18n } from 'vue-i18n'

const auth = useAuthStore()
const route = useRoute()
const { t } = useI18n()
const collapsed = ref(false)

const navItems = computed(() => [
  { path: '/', label: t('nav.dashboard'), icon: LayoutDashboard, requiredView: 'dashboard' },
  { path: '/flujo-operativo', label: t('nav.flujoOperativo'), icon: Landmark, requiredView: 'dashboard' },
  { path: '/crm', label: t('nav.crm'), icon: Users, requiredView: 'crm' },
  { path: '/ventas', label: t('nav.ventas'), icon: ShoppingCart, requiredView: 'ventas' },
  { path: '/compras', label: t('nav.compras'), icon: Package, requiredView: 'compras' },
  { path: '/caja-chica', label: t('nav.cajaChica'), icon: Wallet, requiredView: 'caja_chica' },
  { path: '/taller', label: t('nav.taller'), icon: Wrench, requiredView: 'taller' },
  { path: '/proyectos', label: t('nav.proyectos'), icon: Code2, requiredView: 'proyectos' },
  { path: '/boveda', label: t('nav.boveda'), icon: Lock, requiredView: 'boveda' },
  { path: '/usuarios', label: t('nav.usuarios'), icon: UserCog, requiredView: 'usuarios' },
  { path: '/configuracion', label: t('nav.configuracion'), icon: Settings, requiredView: 'configuracion' },
  { path: '/auditoria', label: 'Auditoría', icon: ClipboardList, requiredView: 'auditoria' },
])

const filteredNavItems = computed(() => {
  const userViews = auth.user?.vistas ?? []
  const hasStar = userViews.includes('*')
  return navItems.value.filter((item) =>
    hasStar || userViews.includes(item.requiredView)
  )
})

function isActive(path: string): boolean {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<template>
  <aside
    :class="[
      'flex flex-col bg-gray-900 text-white transition-all duration-300 ease-in-out h-screen sticky top-0',
      collapsed ? 'w-16' : 'w-64',
    ]"
  >
    <!-- Logo -->
    <div class="flex items-center justify-between px-4 py-5 border-b border-gray-700">
      <div v-if="!collapsed" class="flex items-center gap-2">
        <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-sm">S</div>
        <span class="font-bold text-lg tracking-tight">SOPHIE</span>
      </div>
      <div v-else class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-sm mx-auto">S</div>
      <button
        v-if="!collapsed"
        @click="collapsed = true"
        class="text-gray-400 hover:text-white transition-colors"
      >
        <ChevronLeft :size="18" />
      </button>
    </div>

    <!-- Expand button when collapsed -->
    <button
      v-if="collapsed"
      @click="collapsed = false"
      class="flex justify-center py-2 text-gray-400 hover:text-white transition-colors"
    >
      <ChevronRight :size="18" />
    </button>

    <!-- Nav Items -->
    <nav class="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
      <router-link
        v-for="item in filteredNavItems"
        :key="item.path"
        :to="item.path"
        :class="[
          'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
          isActive(item.path)
            ? 'bg-blue-600 text-white'
            : 'text-gray-400 hover:bg-gray-800 hover:text-white',
          collapsed && 'justify-center',
        ]"
        :title="collapsed ? item.label : undefined"
      >
        <component :is="item.icon" :size="20" class="shrink-0" />
        <span v-if="!collapsed">{{ item.label }}</span>
      </router-link>
    </nav>

    <!-- User info -->
    <div class="border-t border-gray-700 p-4">
      <router-link v-if="!collapsed" to="/perfil" class="flex items-center gap-3 rounded-lg hover:bg-gray-800 px-2 py-2 transition-colors">
        <img
          v-if="auth.user?.foto_perfil_url"
          :src="auth.user.foto_perfil_url"
          alt="Foto de perfil"
          class="w-8 h-8 rounded-full object-cover"
        />
        <div v-else class="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center text-xs font-bold uppercase">
          {{ auth.user?.username?.slice(0, 2) ?? 'US' }}
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium truncate">{{ auth.user?.nombre_completo ?? auth.user?.username }}</p>
          <p class="text-xs text-gray-400 truncate capitalize">{{ auth.user?.rol?.replace('_', ' ') }}</p>
        </div>
      </router-link>
      <router-link v-else to="/perfil" class="flex justify-center rounded-lg hover:bg-gray-800 px-2 py-2 transition-colors">
        <img
          v-if="auth.user?.foto_perfil_url"
          :src="auth.user.foto_perfil_url"
          alt="Foto de perfil"
          class="w-8 h-8 rounded-full object-cover"
        />
        <div v-else class="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center text-xs font-bold uppercase">
          {{ auth.user?.username?.slice(0, 2) ?? 'US' }}
        </div>
      </router-link>
    </div>
  </aside>
</template>

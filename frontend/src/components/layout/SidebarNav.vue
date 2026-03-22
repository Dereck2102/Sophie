<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Blocks,
  Building2,
  LayoutDashboard,
  Landmark,
  Users,
  ShoppingCart,
  Package,
  Wallet,
  Wrench,
  Code2,
  UserCog,
  ClipboardList,
  ChevronLeft,
  ChevronRight,
  Settings,
} from 'lucide-vue-next'
import { useAuthStore } from '../../stores/auth'
import { useSubscriptionStore } from '../../stores/subscription'
import { useI18n } from 'vue-i18n'

const auth = useAuthStore()
const subscription = useSubscriptionStore()
const route = useRoute()
const { t } = useI18n()
const collapsed = ref(false)
const ERP_ONLY_MODE = true
const DISABLED_VIEWS_ERP_ONLY = new Set(['crm'])

const navGroups = computed(() => {
  const userViews = auth.user?.vistas ?? []
  const isSuperadmin = auth.user?.rol === 'superadmin'
  const hasStar = userViews.includes('*')
  const canSee = (view: string) => {
    if (ERP_ONLY_MODE && DISABLED_VIEWS_ERP_ONLY.has(view)) return false
    return hasStar || userViews.includes(view)
  }
  const canSeeModule = (view: string) => isSuperadmin || subscription.hasModuleForView(view)

  const globalGroup = {
    key: 'global',
    label: t('nav.groups.global'),
    items: [
      { path: '/global/dashboard', label: t('nav.globalDashboard'), icon: Blocks, requiredView: 'global_dashboard' },
      { path: '/global/companies', label: t('nav.globalCompanies'), icon: Building2, requiredView: 'global_dashboard' },
      { path: '/global/users', label: t('nav.globalUsers'), icon: Users, requiredView: 'global_dashboard' },
      { path: '/global/configuration', label: t('nav.configuracion'), icon: Settings, requiredView: 'global_dashboard' },
    ].filter(() => isSuperadmin),
  }

  if (isSuperadmin) {
    return [globalGroup].filter(g => g.items.length > 0)
  }

  const groups = [
    {
      key: 'overview',
      label: t('nav.groups.overview'),
      items: [
        { path: '/', label: t('nav.dashboard'), icon: LayoutDashboard, requiredView: 'dashboard' },
        { path: '/flujo-operativo', label: t('nav.flujoOperativo'), icon: Landmark, requiredView: 'dashboard' },
      ].filter(i => canSee(i.requiredView) && canSeeModule(i.requiredView)),
    },
    {
      key: 'operations',
      label: t('nav.groups.operations'),
      items: [
        { path: '/ventas', label: t('nav.ventas'), icon: ShoppingCart, requiredView: 'ventas' },
        { path: '/taller', label: t('nav.taller'), icon: Wrench, requiredView: 'taller' },
        { path: '/proyectos', label: t('nav.proyectos'), icon: Code2, requiredView: 'proyectos' },
        { path: '/compras', label: t('nav.compras'), icon: Package, requiredView: 'compras' },
      ].filter(i => canSee(i.requiredView) && canSeeModule(i.requiredView)),
    },
    {
      key: 'finance',
      label: t('nav.groups.finance'),
      items: [
        { path: '/caja-chica', label: t('nav.cajaChica'), icon: Wallet, requiredView: 'caja_chica' },
        { path: '/empresas', label: t('nav.empresas'), icon: Building2, requiredView: 'empresas' },
      ].filter(i => canSee(i.requiredView) && canSeeModule(i.requiredView)),
    },
    {
      key: 'system',
      label: t('nav.groups.system'),
      items: [
        { path: '/usuarios', label: t('nav.usuarios'), icon: UserCog, requiredView: 'usuarios' },
        { path: '/configuracion', label: t('nav.configuracion'), icon: Settings, requiredView: 'configuracion' },
        { path: '/auditoria', label: 'Auditoría', icon: ClipboardList, requiredView: 'auditoria' },
      ].filter(i => canSee(i.requiredView) && canSeeModule(i.requiredView)),
    },
  ]

  return groups.filter(g => g.items.length > 0)
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

    <!-- Nav Items (grouped) -->
    <nav class="flex-1 px-2 py-4 space-y-4 overflow-y-auto">
      <div v-for="group in navGroups" :key="group.key">
        <!-- Section header (only in expanded mode) -->
        <p
          v-if="!collapsed"
          class="px-3 mb-1 text-[10px] font-semibold uppercase tracking-widest text-gray-500 select-none"
        >
          {{ group.label }}
        </p>
        <!-- Section divider in collapsed mode -->
        <div v-else class="border-t border-gray-700 mx-2 mb-1" />
        <div class="space-y-0.5">
          <router-link
            v-for="item in group.items"
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
        </div>
      </div>
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

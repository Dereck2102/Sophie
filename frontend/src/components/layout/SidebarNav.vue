<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  LayoutDashboard,
  Users,
  ShoppingCart,
  Package,
  Wrench,
  Code2,
  Lock,
  ChevronLeft,
  ChevronRight,
} from 'lucide-vue-next'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const collapsed = ref(false)

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/crm', label: 'CRM', icon: Users },
  { path: '/ventas', label: 'Ventas', icon: ShoppingCart },
  { path: '/compras', label: 'Compras', icon: Package },
  { path: '/taller', label: 'Taller', icon: Wrench },
  { path: '/proyectos', label: 'Proyectos', icon: Code2 },
  { path: '/boveda', label: 'Bóveda', icon: Lock },
]

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
        v-for="item in navItems"
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
      <div v-if="!collapsed" class="flex items-center gap-3">
        <div class="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center text-xs font-bold uppercase">
          {{ auth.user?.username?.slice(0, 2) ?? 'US' }}
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium truncate">{{ auth.user?.nombre_completo ?? auth.user?.username }}</p>
          <p class="text-xs text-gray-400 truncate capitalize">{{ auth.user?.rol?.replace('_', ' ') }}</p>
        </div>
      </div>
      <div v-else class="flex justify-center">
        <div class="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center text-xs font-bold uppercase">
          {{ auth.user?.username?.slice(0, 2) ?? 'US' }}
        </div>
      </div>
    </div>
  </aside>
</template>

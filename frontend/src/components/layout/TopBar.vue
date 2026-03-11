<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Bell, LogOut } from 'lucide-vue-next'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const searchQuery = ref('')

defineProps<{ title?: string }>()

async function handleLogout(): Promise<void> {
  auth.logout()
  await router.push('/login')
}
</script>

<template>
  <header class="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
    <div class="flex items-center gap-4">
      <h1 v-if="title" class="text-lg font-semibold text-gray-800">{{ title }}</h1>
      <div class="relative hidden md:block">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="16" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Buscar..."
          class="pl-9 pr-4 py-2 text-sm bg-gray-100 rounded-lg border-0 focus:ring-2 focus:ring-blue-500 focus:bg-white transition-colors w-64"
        />
      </div>
    </div>

    <div class="flex items-center gap-3">
      <button class="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
        <Bell :size="20" />
        <span class="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
      </button>
      <div class="w-px h-6 bg-gray-200" />
      <router-link
        to="/perfil"
        class="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
      >
        <div class="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center text-white text-xs font-bold uppercase">
          {{ auth.user?.username?.slice(0, 1) ?? 'U' }}
        </div>
        <span class="hidden md:inline max-w-[120px] truncate">{{ auth.user?.nombre_completo ?? auth.user?.username }}</span>
      </router-link>
      <div class="w-px h-6 bg-gray-200" />
      <button
        @click="handleLogout"
        class="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
      >
        <LogOut :size="16" />
        <span class="hidden md:inline">Salir</span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Bell, LogOut, Moon, Sun, Globe } from 'lucide-vue-next'
import { useAuthStore } from '../../stores/auth'
import { useThemeStore } from '../../stores/theme'
import { useI18n } from 'vue-i18n'

const auth = useAuthStore()
const themeStore = useThemeStore()
const router = useRouter()
const { locale, t } = useI18n()
const searchQuery = ref('')

defineProps<{ title?: string }>()

const isDark = computed(() => themeStore.mode === 'dark' || (themeStore.mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches))

function toggleTheme(): void {
  themeStore.setMode(isDark.value ? 'light' : 'dark')
}

function toggleLanguage(): void {
  const newLocale = locale.value === 'es' ? 'en' : 'es'
  locale.value = newLocale
  localStorage.setItem('sophie_locale', newLocale)
}

async function handleLogout(): Promise<void> {
  auth.logout()
  await router.push('/login')
}
</script>

<template>
  <header class="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-6 py-3 flex items-center justify-between transition-colors">
    <div class="flex items-center gap-4">
      <h1 v-if="title" class="text-lg font-semibold text-gray-800 dark:text-gray-100">{{ title }}</h1>
      <div class="relative hidden md:block">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" :size="16" />
        <input
          v-model="searchQuery"
          type="text"
          :placeholder="t('common.search') + '...'"
          class="pl-9 pr-4 py-2 text-sm bg-gray-100 dark:bg-gray-800 dark:text-gray-200 rounded-lg border-0 focus:ring-2 focus:ring-blue-500 focus:bg-white dark:focus:bg-gray-700 transition-colors w-64"
        />
      </div>
    </div>

    <div class="flex items-center gap-3">
      <!-- Language toggle -->
      <button
        @click="toggleLanguage"
        class="flex items-center gap-1.5 p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors text-xs font-medium"
        :title="t('common.language')"
      >
        <Globe :size="16" />
        <span class="hidden sm:inline uppercase">{{ locale }}</span>
      </button>

      <!-- Theme toggle -->
      <button
        @click="toggleTheme"
        class="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
        :title="isDark ? t('common.lightMode') : t('common.darkMode')"
      >
        <Sun v-if="isDark" :size="20" />
        <Moon v-else :size="20" />
      </button>

      <!-- Notifications -->
      <button class="relative p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
        <Bell :size="20" />
        <span class="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
      </button>
      <div class="w-px h-6 bg-gray-200 dark:bg-gray-700" />
      <router-link
        to="/perfil"
        class="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
      >
        <div class="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center text-white text-xs font-bold uppercase">
          {{ auth.user?.username?.slice(0, 1) ?? 'U' }}
        </div>
        <span class="hidden md:inline max-w-[120px] truncate">{{ auth.user?.nombre_completo ?? auth.user?.username }}</span>
      </router-link>
      <div class="w-px h-6 bg-gray-200 dark:bg-gray-700" />
      <button
        @click="handleLogout"
        class="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
      >
        <LogOut :size="16" />
        <span class="hidden md:inline">{{ t('common.logout') }}</span>
      </button>
    </div>
  </header>
</template>

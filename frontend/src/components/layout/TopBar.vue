<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Bell, LogOut, Moon, Sun, Globe, TriangleAlert, Info, ShieldAlert } from 'lucide-vue-next'
import { useAuthStore } from '../../stores/auth'
import { useThemeStore } from '../../stores/theme'
import { useI18n } from 'vue-i18n'
import { useNotificationStore } from '../../stores/notifications'
import { useSubscriptionStore } from '../../stores/subscription'

const auth = useAuthStore()
const themeStore = useThemeStore()
const notificationStore = useNotificationStore()
const subscriptionStore = useSubscriptionStore()
const router = useRouter()
const { locale, t } = useI18n()
const searchQuery = ref('')
const showNotifications = ref(false)

defineProps<{ title?: string }>()

const isDark = computed(() => themeStore.mode === 'dark' || (themeStore.mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches))

const hasNotifications = computed(() => notificationStore.unreadCount > 0)

const showSubscriptionBadge = computed(() => Boolean(auth.isEnterpriseUser && subscriptionStore.current))

const subscriptionStatusInfo = computed(() => {
  const status = subscriptionStore.current?.status
  if (!status) return null

  if (status === 'active' || status === 'trial') {
    return {
      label: t('topbar.subscription.activeLabel'),
      detail: t('topbar.subscription.activeDetail'),
      className: 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/25 dark:text-green-300 dark:border-green-700',
    }
  }

  if (status === 'pending') {
    return {
      label: t('topbar.subscription.pendingLabel'),
      detail: t('topbar.subscription.pendingDetail'),
      className: 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-900/25 dark:text-amber-300 dark:border-amber-700',
    }
  }

  if (status === 'past_due') {
    return {
      label: t('topbar.subscription.pastDueLabel'),
      detail: t('topbar.subscription.pastDueDetail'),
      className: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/25 dark:text-red-300 dark:border-red-700',
    }
  }

  return {
    label: t('topbar.subscription.inactiveLabel'),
    detail: t('topbar.subscription.inactiveDetail'),
    className: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
  }
})

onMounted(() => {
  notificationStore.fetchNotifications(false)
  if (auth.user?.rol && auth.isEnterpriseUser && !subscriptionStore.initialized) {
    void subscriptionStore.bootstrapForCurrentUser(auth.user)
  }
})

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

async function toggleNotifications(): Promise<void> {
  showNotifications.value = !showNotifications.value
  if (showNotifications.value) {
    await notificationStore.fetchNotifications(true)
  }
}

async function openNotification(route: string): Promise<void> {
  showNotifications.value = false
  await router.push(route)
}

function notificationIcon(severity: 'info' | 'warning' | 'critical') {
  if (severity === 'critical') return TriangleAlert
  if (severity === 'warning') return ShieldAlert
  return Info
}
</script>

<template>
  <header class="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-6 py-3 flex items-center justify-between transition-colors">
    <div class="flex items-center gap-4">
      <h1 v-if="title" class="text-lg font-semibold text-gray-800 dark:text-gray-100">{{ title }}</h1>
      <div
        v-if="showSubscriptionBadge && subscriptionStatusInfo"
        :class="['hidden lg:inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium', subscriptionStatusInfo.className]"
        :title="subscriptionStatusInfo.detail"
      >
        <span>{{ subscriptionStatusInfo.label }}</span>
      </div>
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
      <div class="relative">
      <button
        @click="toggleNotifications"
        class="relative p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
      >
        <Bell :size="20" />
        <span v-if="hasNotifications" class="absolute top-1 right-1 min-w-4 h-4 px-1 bg-red-500 rounded-full text-[10px] leading-4 text-white text-center">
          {{ notificationStore.unreadCount }}
        </span>
      </button>
      <div v-if="showNotifications" class="absolute right-0 mt-2 w-96 max-w-[calc(100vw-2rem)] bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-xl z-50 overflow-hidden">
        <div class="px-4 py-3 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
          <div>
            <p class="text-sm font-semibold text-gray-800 dark:text-gray-100">{{ t('topbar.notifications') }}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">{{ t('topbar.erpAlerts') }}</p>
          </div>
          <button @click="notificationStore.fetchNotifications(true)" class="text-xs text-blue-600 hover:text-blue-700">{{ t('topbar.refresh') }}</button>
        </div>
        <div v-if="notificationStore.loading" class="px-4 py-6 text-sm text-gray-500 dark:text-gray-400">
          {{ t('topbar.loadingAlerts') }}
        </div>
        <div v-else-if="notificationStore.items.length === 0" class="px-4 py-6 text-sm text-gray-500 dark:text-gray-400">
          {{ t('topbar.noAlerts') }}
        </div>
        <div v-else class="max-h-96 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-800">
          <button
            v-for="item in notificationStore.items"
            :key="item.id"
            @click="openNotification(item.route)"
            class="w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors flex gap-3"
          >
            <component :is="notificationIcon(item.severity)" :size="18" :class="[
              'mt-0.5 shrink-0',
              item.severity === 'critical' ? 'text-red-500' : item.severity === 'warning' ? 'text-amber-500' : 'text-blue-500',
            ]" />
            <div>
              <p class="text-sm font-medium text-gray-800 dark:text-gray-100">{{ item.title }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ item.description }}</p>
            </div>
          </button>
        </div>
      </div>
      </div>
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

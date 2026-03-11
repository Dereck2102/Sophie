<script setup lang="ts">
import { ref } from 'vue'
import { CheckCircle } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import { useThemeStore, type ThemeMode } from '../stores/theme'
import { useI18n } from 'vue-i18n'

const themeStore = useThemeStore()
const { t, locale } = useI18n()

const savedSuccess = ref(false)

const platformConfig = ref({
  companyName: localStorage.getItem('sophie_company_name') ?? 'SOPHIE ERP/CRM',
  timezone: localStorage.getItem('sophie_timezone') ?? 'America/Guayaquil',
  market: localStorage.getItem('sophie_market') ?? 'EC',
  emailNotifications: localStorage.getItem('sophie_email_notif') !== 'false',
  systemNotifications: localStorage.getItem('sophie_sys_notif') !== 'false',
  sessionTimeout: Number(localStorage.getItem('sophie_session_timeout') ?? 30),
  requireMFA: localStorage.getItem('sophie_require_mfa') === 'true',
  maxLoginAttempts: Number(localStorage.getItem('sophie_max_login') ?? 5),
})

const timezones = [
  { value: 'America/Guayaquil', label: 'Ecuador (GMT-5)' },
  { value: 'America/New_York', label: 'Eastern US (GMT-5/-4)' },
  { value: 'America/Chicago', label: 'Central US (GMT-6/-5)' },
  { value: 'America/Denver', label: 'Mountain US (GMT-7/-6)' },
  { value: 'America/Los_Angeles', label: 'Pacific US (GMT-8/-7)' },
  { value: 'Europe/London', label: 'London (GMT+0/+1)' },
  { value: 'Europe/Paris', label: 'Paris/Madrid (GMT+1/+2)' },
  { value: 'Europe/Berlin', label: 'Berlin/Amsterdam (GMT+1/+2)' },
]

const markets = [
  { value: 'EC', label: 'Ecuador' },
  { value: 'US', label: 'United States' },
  { value: 'EU', label: 'Europe' },
]

const themes: { value: ThemeMode; labelKey: string }[] = [
  { value: 'light', labelKey: 'config.themeLight' },
  { value: 'dark', labelKey: 'config.themeDark' },
  { value: 'system', labelKey: 'config.themeSystem' },
]

function setLanguage(lang: string): void {
  locale.value = lang
  localStorage.setItem('sophie_locale', lang)
}

function savePlatformConfig(): void {
  localStorage.setItem('sophie_company_name', platformConfig.value.companyName)
  localStorage.setItem('sophie_timezone', platformConfig.value.timezone)
  localStorage.setItem('sophie_market', platformConfig.value.market)
  localStorage.setItem('sophie_email_notif', String(platformConfig.value.emailNotifications))
  localStorage.setItem('sophie_sys_notif', String(platformConfig.value.systemNotifications))
  localStorage.setItem('sophie_session_timeout', String(platformConfig.value.sessionTimeout))
  localStorage.setItem('sophie_require_mfa', String(platformConfig.value.requireMFA))
  localStorage.setItem('sophie_max_login', String(platformConfig.value.maxLoginAttempts))
  savedSuccess.value = true
  setTimeout(() => { savedSuccess.value = false }, 3000)
}
</script>

<template>
  <div class="space-y-6 max-w-4xl">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ t('config.title') }}</h1>
      <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">{{ t('config.subtitle') }}</p>
    </div>

    <!-- Success Banner -->
    <div v-if="savedSuccess" class="flex items-center gap-2 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300 px-4 py-3 rounded-xl text-sm">
      <CheckCircle :size="16" />
      {{ t('config.saved') }}
    </div>

    <!-- Appearance -->
    <Card :title="t('config.appearance')">
      <div class="space-y-5">
        <!-- Theme -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{{ t('config.theme') }}</label>
          <div class="flex gap-3">
            <button
              v-for="theme in themes"
              :key="theme.value"
              @click="themeStore.setMode(theme.value)"
              :class="[
                'flex-1 py-2.5 px-4 rounded-xl border-2 text-sm font-medium transition-all',
                themeStore.mode === theme.value
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                  : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-500'
              ]"
            >
              {{ t(theme.labelKey) }}
            </button>
          </div>
        </div>

        <!-- Language -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{{ t('config.language') }}</label>
          <div class="flex gap-3">
            <button
              @click="setLanguage('es')"
              :class="[
                'flex-1 py-2.5 px-4 rounded-xl border-2 text-sm font-medium transition-all',
                locale === 'es'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                  : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-300'
              ]"
            >
              🇪🇸 {{ t('config.languageES') }}
            </button>
            <button
              @click="setLanguage('en')"
              :class="[
                'flex-1 py-2.5 px-4 rounded-xl border-2 text-sm font-medium transition-all',
                locale === 'en'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                  : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-300'
              ]"
            >
              🇺🇸 {{ t('config.languageEN') }}
            </button>
          </div>
        </div>
      </div>
    </Card>

    <!-- Platform Settings -->
    <Card :title="t('config.platform')">
      <div class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('config.companyName') }}</label>
            <input
              v-model="platformConfig.companyName"
              type="text"
              class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('config.market') }}</label>
            <select
              v-model="platformConfig.market"
              class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100"
            >
              <option v-for="m in markets" :key="m.value" :value="m.value">{{ m.label }}</option>
            </select>
          </div>

          <div class="sm:col-span-2">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('config.timezone') }}</label>
            <select
              v-model="platformConfig.timezone"
              class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100"
            >
              <option v-for="tz in timezones" :key="tz.value" :value="tz.value">{{ tz.label }}</option>
            </select>
          </div>
        </div>
      </div>
    </Card>

    <!-- Security Settings -->
    <Card :title="t('config.security')">
      <div class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('config.sessionTimeout') }}</label>
            <input
              v-model.number="platformConfig.sessionTimeout"
              type="number"
              min="5"
              max="480"
              class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('config.maxLoginAttempts') }}</label>
            <input
              v-model.number="platformConfig.maxLoginAttempts"
              type="number"
              min="3"
              max="10"
              class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100"
            />
          </div>
        </div>
        <div class="flex items-center gap-3">
          <input
            id="requireMFA"
            v-model="platformConfig.requireMFA"
            type="checkbox"
            class="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
          />
          <label for="requireMFA" class="text-sm text-gray-700 dark:text-gray-300">{{ t('config.requireMFA') }}</label>
        </div>
      </div>
    </Card>

    <!-- Notifications -->
    <Card :title="t('config.notifications')">
      <div class="space-y-3">
        <div class="flex items-center gap-3">
          <input
            id="emailNotif"
            v-model="platformConfig.emailNotifications"
            type="checkbox"
            class="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
          />
          <label for="emailNotif" class="text-sm text-gray-700 dark:text-gray-300">{{ t('config.emailNotifications') }}</label>
        </div>
        <div class="flex items-center gap-3">
          <input
            id="sysNotif"
            v-model="platformConfig.systemNotifications"
            type="checkbox"
            class="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
          />
          <label for="sysNotif" class="text-sm text-gray-700 dark:text-gray-300">{{ t('config.systemNotifications') }}</label>
        </div>
      </div>
    </Card>

    <!-- Save Button -->
    <div class="flex justify-end">
      <Button @click="savePlatformConfig">
        {{ t('common.save') }}
      </Button>
    </div>
  </div>
</template>

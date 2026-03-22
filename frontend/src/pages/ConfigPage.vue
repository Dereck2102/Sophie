<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CheckCircle, Download, Upload } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import ImageUpload from '../components/ui/ImageUpload.vue'
import api from '../services/api'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { useSubscriptionStore } from '../stores/subscription'
import type {
  AuthChannelsStatus,
  BackupUsuariosPayload,
  BillingCycle,
  CheckoutResponse,
  ConfiguracionSistema,
  CustomOrderResponse,
  EmpresaSubscription,
  PaymentGatewayConfig,
  PendingCustomOrder,
  PlanPreset,
  SubscriptionPlanTier,
  SubscriptionStatus,
} from '../types'

const loading = ref(true)
const saving = ref(false)
const restoring = ref(false)
const checkingChannels = ref(false)
const testingEmail = ref(false)
const testingSms = ref(false)
const loadingSubscriptions = ref(false)
const savingSubscription = ref(false)
const creatingCheckout = ref(false)
const creatingCustomOrder = ref(false)
const loadingGateways = ref(false)
const savingGateway = ref(false)
const activatingOrder = ref(false)
const success = ref<string | null>(null)
const error = ref<string | null>(null)
const { t } = useI18n()
const auth = useAuthStore()
const subscriptionStore = useSubscriptionStore()

const channelStatus = ref<AuthChannelsStatus | null>(null)
const testEmail = ref('')
const testPhone = ref('')
const planPresets = ref<PlanPreset[]>([])
const companySubscriptions = ref<EmpresaSubscription[]>([])
const gateways = ref<PaymentGatewayConfig[]>([])
const pendingCustomOrders = ref<PendingCustomOrder[]>([])
const subForm = ref<{
  id_empresa: number | null
  plan_tier: SubscriptionPlanTier
  billing_cycle: BillingCycle
  status: SubscriptionStatus
  custom_notes: string
  feature_overrides_text: string
}>({
  id_empresa: null,
  plan_tier: 'starter',
  billing_cycle: 'monthly',
  status: 'active',
  custom_notes: '',
  feature_overrides_text: '',
})
const payphoneForm = ref({
  enabled: false,
  endpoint_url: 'https://pay.payphonetodoesposible.com/api/button/Prepare',
  store_id: '',
  public_key: '',
  secret: '',
  return_url: '',
  cancel_url: '',
  webhook_token: '',
  has_webhook_token: false,
})
const customOrderForm = ref({
  id_empresa: null as number | null,
  billing_cycle: 'monthly' as BillingCycle,
  amount_usd: 0,
  feature_overrides_text: '',
  custom_requirements: '',
  generate_payphone_checkout: false,
})

const isEnterpriseUser = computed(() => Boolean(auth.user && auth.user.rol !== 'superadmin'))
const companyPlanName = computed(() => {
  const tier = subscriptionStore.current?.plan_tier
  if (!tier) return '—'
  return t(`perfil.planTiers.${tier}`)
})
const companyModuleLabels = computed(() =>
  subscriptionStore.activeModules.map((moduleCode) => ({
    code: moduleCode,
    label: t(`perfil.moduleNames.${moduleCode}`),
  }))
)

const form = ref<ConfiguracionSistema>({
  nombre_instancia: 'SOPHIE',
  nombre_empresa: 'Big Solutions',
  ruc_empresa: '',
  logo_empresa_url: '',
  timezone: 'America/Guayaquil',
  market: 'EC',
  email_notifications: true,
  system_notifications: true,
  session_timeout_minutes: 30,
  require_mfa_global: false,
  auth_twofa_enabled: false,
  auth_channel_email_enabled: true,
  auth_channel_sms_enabled: true,
  auth_channel_app_enabled: true,
  max_login_attempts: 5,
  color_primario: '#2563eb',
  color_secundario: '#0f172a',
  reporte_footer: '',
  iva_default_percent: 15,
  descuento_default_percent: 0,
  costo_hora_tecnica_default: 25,
  costo_movilizacion_default: 0,
  costo_software_default: 0,
  costo_material_default: 0,
  costo_mano_obra_default: 0,
  fondo_caja_chica_mensual: 0,
})

async function loadSettings(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get<ConfiguracionSistema>('/api/v1/admin/settings')
    form.value = data
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? t('configPage.loadError')
  } finally {
    loading.value = false
  }
}

async function loadChannelStatus(): Promise<void> {
  checkingChannels.value = true
  try {
    const { data } = await api.get<AuthChannelsStatus>('/api/v1/admin/auth/channels/status')
    channelStatus.value = data
  } catch {
    channelStatus.value = null
  } finally {
    checkingChannels.value = false
  }
}

async function saveSettings(): Promise<void> {
  saving.value = true
  success.value = null
  error.value = null
  try {
    const { data } = await api.patch<ConfiguracionSistema>('/api/v1/admin/settings', form.value)
    form.value = data
    success.value = t('configPage.saved')
    await loadChannelStatus()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? t('configPage.saveError')
  } finally {
    saving.value = false
  }
}

async function runEmailTest(): Promise<void> {
  testingEmail.value = true
  success.value = null
  error.value = null
  try {
    const { data } = await api.post<{ detail: string }>('/api/v1/admin/auth/channels/test-email', {
      to_email: testEmail.value || undefined,
    })
    success.value = data.detail
    await loadChannelStatus()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? t('configPage.testEmailError')
  } finally {
    testingEmail.value = false
  }
}

async function runSmsTest(): Promise<void> {
  if (!testPhone.value.trim()) {
    error.value = t('configPage.enterSmsNumber')
    return
  }
  testingSms.value = true
  success.value = null
  error.value = null
  try {
    const { data } = await api.post<{ detail: string }>('/api/v1/admin/auth/channels/test-sms', {
      to_phone: testPhone.value,
    })
    success.value = data.detail
    await loadChannelStatus()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? t('configPage.testSmsError')
  } finally {
    testingSms.value = false
  }
}

async function loadSubscriptionsData(): Promise<void> {
  loadingSubscriptions.value = true
  try {
    const [plansRes, companiesRes] = await Promise.all([
      api.get<PlanPreset[]>('/api/v1/subscriptions/plans'),
      api.get<EmpresaSubscription[]>('/api/v1/admin/subscriptions/companies', { params: { limit: 300 } }),
    ])
    planPresets.value = plansRes.data
    companySubscriptions.value = companiesRes.data

    if (!subForm.value.id_empresa && companiesRes.data.length > 0) {
      const first = companiesRes.data[0]
      if (first) {
        subForm.value.id_empresa = first.id_empresa
        subForm.value.plan_tier = first.plan_tier
        subForm.value.billing_cycle = first.billing_cycle
        subForm.value.status = first.status
        subForm.value.custom_notes = first.custom_notes ?? ''
        subForm.value.feature_overrides_text = first.features.join(', ')
        customOrderForm.value.id_empresa = first.id_empresa
      }
    }
  } catch {
    // fallback no-op; main config page should still load
  } finally {
    loadingSubscriptions.value = false
  }
}

async function loadPendingCustomOrders(): Promise<void> {
  try {
    const { data } = await api.get<PendingCustomOrder[]>('/api/v1/admin/subscriptions/custom-orders/pending', {
      params: { limit: 300 },
    })
    pendingCustomOrders.value = data
  } catch {
    pendingCustomOrders.value = []
  }
}

async function loadGatewayConfigs(): Promise<void> {
  loadingGateways.value = true
  try {
    const { data } = await api.get<PaymentGatewayConfig[]>('/api/v1/admin/subscriptions/gateways')
    gateways.value = data
    const payphone = data.find((item) => item.provider === 'payphone')
    if (payphone) {
      payphoneForm.value.enabled = payphone.enabled
      payphoneForm.value.endpoint_url = payphone.endpoint_url || payphoneForm.value.endpoint_url
      payphoneForm.value.store_id = payphone.store_id || ''
      payphoneForm.value.public_key = payphone.public_key || ''
      payphoneForm.value.return_url = payphone.return_url || ''
      payphoneForm.value.cancel_url = payphone.cancel_url || ''
      payphoneForm.value.has_webhook_token = !!payphone.has_webhook_token
      payphoneForm.value.secret = ''
      payphoneForm.value.webhook_token = ''
    }
  } catch {
    // keep section non-blocking
  } finally {
    loadingGateways.value = false
  }
}

async function savePayphoneConfig(): Promise<void> {
  savingGateway.value = true
  success.value = null
  error.value = null
  try {
    await api.put('/api/v1/admin/subscriptions/gateways/payphone', {
      provider: 'payphone',
      enabled: payphoneForm.value.enabled,
      endpoint_url: payphoneForm.value.endpoint_url || null,
      store_id: payphoneForm.value.store_id || null,
      public_key: payphoneForm.value.public_key || null,
      secret: payphoneForm.value.secret,
      return_url: payphoneForm.value.return_url || null,
      cancel_url: payphoneForm.value.cancel_url || null,
      webhook_token: payphoneForm.value.webhook_token,
    })
    payphoneForm.value.secret = ''
    payphoneForm.value.webhook_token = ''
    success.value = t('configPage.gatewaySaved')
    await loadGatewayConfigs()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? t('configPage.gatewaySaveError')
  } finally {
    savingGateway.value = false
  }
}

function onCompanyChange(): void {
  const selected = companySubscriptions.value.find((item) => item.id_empresa === subForm.value.id_empresa)
  if (!selected) return
  subForm.value.plan_tier = selected.plan_tier
  subForm.value.billing_cycle = selected.billing_cycle
  subForm.value.status = selected.status
  subForm.value.custom_notes = selected.custom_notes ?? ''
  subForm.value.feature_overrides_text = selected.features.join(', ')
  customOrderForm.value.id_empresa = selected.id_empresa
}

async function saveCompanySubscription(): Promise<void> {
  if (!subForm.value.id_empresa) {
    error.value = t('configPage.selectCompanyFirst')
    return
  }
  savingSubscription.value = true
  success.value = null
  error.value = null
  try {
    const featureOverrides = subForm.value.feature_overrides_text
      .split(/[\n,]/)
      .map((item) => item.trim())
      .filter(Boolean)
    await api.put(`/api/v1/admin/subscriptions/companies/${subForm.value.id_empresa}`, {
      plan_tier: subForm.value.plan_tier,
      billing_cycle: subForm.value.billing_cycle,
      status: subForm.value.status,
      custom_notes: subForm.value.custom_notes || null,
      feature_overrides: featureOverrides,
    })
    success.value = t('configPage.subscriptionSaved')
    await loadSubscriptionsData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? t('configPage.subscriptionSaveError')
  } finally {
    savingSubscription.value = false
  }
}

async function createPlanCheckout(): Promise<void> {
  creatingCheckout.value = true
  success.value = null
  error.value = null
  try {
    const { data } = await api.post<CheckoutResponse>('/api/v1/subscriptions/checkout', {
      plan: subForm.value.plan_tier,
      billing_cycle: subForm.value.billing_cycle,
      id_empresa: subForm.value.id_empresa,
      custom_requirements: subForm.value.plan_tier === 'custom' ? subForm.value.custom_notes : undefined,
    })
    success.value = `${data.detail} #${data.id_pago}`
    if (data.checkout_url) {
      window.open(data.checkout_url, '_blank', 'noopener,noreferrer')
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? t('configPage.checkoutCreateError')
  } finally {
    creatingCheckout.value = false
  }
}

async function createCustomOrder(): Promise<void> {
  if (!customOrderForm.value.id_empresa) {
    error.value = t('configPage.selectCompanyFirst')
    return
  }
  if (!customOrderForm.value.custom_requirements.trim()) {
    error.value = t('configPage.customOrderRequirementsRequired')
    return
  }

  creatingCustomOrder.value = true
  error.value = null
  success.value = null
  try {
    const featureOverrides = customOrderForm.value.feature_overrides_text
      .split(/[\n,]/)
      .map((item) => item.trim())
      .filter(Boolean)

    const { data } = await api.post<CustomOrderResponse>('/api/v1/admin/subscriptions/custom-orders', {
      id_empresa: customOrderForm.value.id_empresa,
      billing_cycle: customOrderForm.value.billing_cycle,
      amount_usd: customOrderForm.value.amount_usd,
      custom_requirements: customOrderForm.value.custom_requirements,
      feature_overrides: featureOverrides,
      generate_payphone_checkout: customOrderForm.value.generate_payphone_checkout,
    })

    success.value = `${data.detail} ${data.order_number}`
    if (data.checkout_url) {
      window.open(data.checkout_url, '_blank', 'noopener,noreferrer')
    }
    await loadPendingCustomOrders()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? t('configPage.customOrderCreateError')
  } finally {
    creatingCustomOrder.value = false
  }
}

async function activateCustomOrder(id_pago: number): Promise<void> {
  activatingOrder.value = true
  error.value = null
  success.value = null

  try {
    interface ActivateOrderResponse {
      id_pago: number
      id_empresa: number
      plan_tier: SubscriptionPlanTier
      status: SubscriptionStatus
      features: string[]
      detail: string
    }
    const { data } = await api.post<ActivateOrderResponse>(
      `/api/v1/admin/subscriptions/custom-orders/${id_pago}/activate`,
      {}
    )
    success.value = t('configPage.customOrderActivated', { order: `#${data.id_pago}` })
    await loadSubscriptionsData()
    await loadPendingCustomOrders()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? t('configPage.customOrderActivateError')
  } finally {
    activatingOrder.value = false
  }
}

async function downloadBackup(): Promise<void> {
  error.value = null
  success.value = null
  try {
    const { data } = await api.get<BackupUsuariosPayload>('/api/v1/admin/backup/usuarios')
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `sophie-backup-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.json`
    link.click()
    URL.revokeObjectURL(url)
    success.value = t('configPage.backupDownloaded')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? t('configPage.backupDownloadError')
  }
}

async function handleRestore(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.item(0)
  if (!file) return
  restoring.value = true
  error.value = null
  success.value = null
  try {
    const raw = await file.text()
    const payload = JSON.parse(raw)
    await api.post('/api/v1/admin/restore/usuarios', payload)
    success.value = t('configPage.backupRestored')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? t('configPage.backupRestoreError')
  } finally {
    restoring.value = false
    input.value = ''
  }
}

onMounted(async () => {
  if (auth.user?.rol && auth.user.rol !== 'superadmin' && !subscriptionStore.initialized) {
    await subscriptionStore.bootstrapForCurrentUser(auth.user)
  }
  await loadSettings()
  await loadChannelStatus()
  await loadSubscriptionsData()
  await loadPendingCustomOrders()
  await loadGatewayConfigs()
})
</script>

<template>
  <div class="space-y-6 max-w-5xl">
    <div>
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{{ t('configPage.globalTitle') }}</h1>
      <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">{{ t('configPage.globalSubtitle') }}</p>
    </div>

    <div v-if="success" class="flex items-center gap-2 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-xl text-sm">
      <CheckCircle :size="16" /> {{ success }}
    </div>
    <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
      {{ error }}
    </div>

    <Card v-if="isEnterpriseUser" :title="t('configPage.companyPlanTitle')">
      <div class="space-y-3 text-sm">
        <p class="text-gray-600 dark:text-gray-300">{{ t('configPage.companyPlanHint') }}</p>
        <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between py-2 border-b border-gray-100 dark:border-gray-700">
          <span class="text-gray-500 dark:text-gray-400">{{ t('perfil.currentPlan') }}</span>
          <span class="font-semibold text-blue-700 dark:text-blue-400">{{ companyPlanName }}</span>
        </div>
        <div>
          <p class="text-gray-500 dark:text-gray-400 mb-2">{{ t('perfil.enabledModules') }}</p>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="item in companyModuleLabels"
              :key="`config-${item.code}`"
              class="inline-flex items-center rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2.5 py-1 text-xs font-medium"
            >
              {{ item.code }} · {{ item.label }}
            </span>
            <span v-if="companyModuleLabels.length === 0" class="text-gray-400 text-xs">{{ t('perfil.noPlanContext') }}</span>
          </div>
        </div>
      </div>
    </Card>

    <Card :title="t('configPage.brandingTitle')">
      <div v-if="loading" class="text-sm text-gray-500 dark:text-gray-400">{{ t('common.loading') }}</div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.instanceName') }}</label>
          <input v-model="form.nombre_instancia" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('config.companyName') }}</label>
          <input v-model="form.nombre_empresa" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.taxId') }}</label>
          <input v-model="form.ruc_empresa" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('config.companyLogo') }}</label>
          <ImageUpload
            v-model="form.logo_empresa_url"
            image-type="profile"
            :target-width="600"
            accept="image/png,image/jpeg,image/webp"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.primaryColor') }}</label>
          <input v-model="form.color_primario" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.secondaryColor') }}</label>
          <input v-model="form.color_secundario" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.reportFooter') }}</label>
          <textarea v-model="form.reporte_footer" rows="2" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none" />
        </div>
      </div>
    </Card>

    <Card :title="t('configPage.securityTitle')">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('config.timezone') }}</label>
          <input v-model="form.timezone" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('config.market') }}</label>
          <input v-model="form.market" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('config.sessionTimeout') }}</label>
          <input v-model.number="form.session_timeout_minutes" type="number" min="5" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('config.maxLoginAttempts') }}</label>
          <input v-model.number="form.max_login_attempts" type="number" min="1" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <label class="flex items-center gap-3 text-sm text-gray-700 dark:text-gray-300">
          <input v-model="form.require_mfa_global" type="checkbox" class="w-4 h-4" /> {{ t('config.requireMFA') }}
        </label>
        <label class="flex items-center gap-3 text-sm text-gray-700">
          <input v-model="form.auth_twofa_enabled" type="checkbox" class="w-4 h-4" /> Activar verificación 2FA en login
        </label>
        <label class="flex items-center gap-3 text-sm text-gray-700">
          <input v-model="form.auth_channel_email_enabled" type="checkbox" class="w-4 h-4" /> Canal 2FA por correo
        </label>
        <label class="flex items-center gap-3 text-sm text-gray-700">
          <input v-model="form.auth_channel_sms_enabled" type="checkbox" class="w-4 h-4" /> Canal 2FA por SMS
        </label>
        <label class="flex items-center gap-3 text-sm text-gray-700 md:col-span-2">
          <input v-model="form.auth_channel_app_enabled" type="checkbox" class="w-4 h-4" /> Canal 2FA por app autenticadora
        </label>
        <label class="flex items-center gap-3 text-sm text-gray-700">
          <input v-model="form.email_notifications" type="checkbox" class="w-4 h-4" /> Notificaciones por email
        </label>
        <label class="flex items-center gap-3 text-sm text-gray-700 md:col-span-2">
          <input v-model="form.system_notifications" type="checkbox" class="w-4 h-4" /> Notificaciones del sistema
        </label>
      </div>
    </Card>

    <Card :title="t('configPage.authChannelsTitle')">
      <div class="space-y-4">
        <div v-if="checkingChannels" class="text-sm text-gray-500 dark:text-gray-400">{{ t('configPage.checkingChannels') }}</div>
        <div v-else-if="channelStatus" class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          <div class="flex items-center justify-between rounded-lg border px-3 py-2">
            <span>2FA (entorno)</span>
            <span :class="channelStatus.twofa_env_enabled ? 'text-green-700' : 'text-red-600'" class="font-medium">
              {{ channelStatus.twofa_env_enabled ? 'Activo' : 'Inactivo' }}
            </span>
          </div>
          <div class="flex items-center justify-between rounded-lg border px-3 py-2">
            <span>2FA (configuración)</span>
            <span :class="channelStatus.twofa_enabled ? 'text-green-700' : 'text-red-600'" class="font-medium">
              {{ channelStatus.twofa_enabled ? 'Activo' : 'Inactivo' }}
            </span>
          </div>
          <div class="flex items-center justify-between rounded-lg border px-3 py-2">
            <span>Canal correo</span>
            <span :class="channelStatus.email_effective ? 'text-green-700' : 'text-amber-700'" class="font-medium">
              {{ channelStatus.email_effective ? 'Operativo' : 'No operativo' }}
            </span>
          </div>
          <div class="flex items-center justify-between rounded-lg border px-3 py-2">
            <span>Canal SMS</span>
            <span :class="channelStatus.sms_effective ? 'text-green-700' : 'text-amber-700'" class="font-medium">
              {{ channelStatus.sms_effective ? 'Operativo' : 'No operativo' }}
            </span>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="space-y-2">
            <label class="block text-sm font-medium text-gray-700">Probar correo</label>
            <input
              v-model="testEmail"
              type="email"
              placeholder="correo@dominio.com (opcional)"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
            <Button :loading="testingEmail" type="button" @click="runEmailTest">{{ t('configPage.sendTestEmail') }}</Button>
          </div>

          <div class="space-y-2">
            <label class="block text-sm font-medium text-gray-700">Probar SMS</label>
            <input
              v-model="testPhone"
              type="text"
              placeholder="+593..."
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
            <Button :loading="testingSms" type="button" @click="runSmsTest">{{ t('configPage.sendTestSms') }}</Button>
          </div>
        </div>
      </div>
    </Card>

    <Card :title="t('configPage.financialTitle')">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">IVA por defecto (%)</label>
          <input v-model.number="form.iva_default_percent" type="number" min="0" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Descuento por defecto (%)</label>
          <input v-model.number="form.descuento_default_percent" type="number" min="0" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Costo hora técnica</label>
          <input v-model.number="form.costo_hora_tecnica_default" type="number" min="0" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Costo mano de obra</label>
          <input v-model.number="form.costo_mano_obra_default" type="number" min="0" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Costo materiales</label>
          <input v-model.number="form.costo_material_default" type="number" min="0" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Costo movilización</label>
          <input v-model.number="form.costo_movilizacion_default" type="number" min="0" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Costo software</label>
          <input v-model.number="form.costo_software_default" type="number" min="0" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Fondo mensual de caja chica</label>
          <input v-model.number="form.fondo_caja_chica_mensual" type="number" min="0" step="0.01" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          <p class="text-xs text-gray-500 mt-1">Este valor se usa como base mensual para el control de caja chica.</p>
        </div>
      </div>
    </Card>

    <Card :title="t('configPage.subscriptionsTitle')">
      <div v-if="loadingSubscriptions" class="text-sm text-gray-500 dark:text-gray-400">{{ t('common.loading') }}</div>
      <div v-else class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.company') }}</label>
            <select v-model.number="subForm.id_empresa" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" @change="onCompanyChange">
              <option :value="null">{{ t('configPage.selectCompany') }}</option>
              <option v-for="item in companySubscriptions" :key="item.id_empresa" :value="item.id_empresa">
                {{ item.empresa_nombre }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.plan') }}</label>
            <select v-model="subForm.plan_tier" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
              <option v-for="plan in planPresets" :key="plan.plan" :value="plan.plan">
                {{ plan.name }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.billingCycle') }}</label>
            <select v-model="subForm.billing_cycle" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
              <option value="monthly">{{ t('configPage.monthly') }}</option>
              <option value="yearly">{{ t('configPage.yearly') }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.subscriptionStatus') }}</label>
            <select v-model="subForm.status" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
              <option value="active">Active</option>
              <option value="trial">Trial</option>
              <option value="past_due">Past Due</option>
              <option value="canceled">Canceled</option>
              <option value="pending">Pending</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.featureOverrides') }}</label>
          <textarea
            v-model="subForm.feature_overrides_text"
            rows="3"
            :placeholder="t('configPage.featureOverridesHint')"
            class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-y"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.customNotes') }}</label>
          <textarea
            v-model="subForm.custom_notes"
            rows="2"
            :placeholder="t('configPage.customNotesHint')"
            class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-y"
          />
        </div>

        <div class="flex flex-wrap gap-3">
          <Button :loading="savingSubscription" type="button" @click="saveCompanySubscription">
            {{ t('configPage.saveSubscription') }}
          </Button>
          <Button :loading="creatingCheckout" type="button" variant="secondary" @click="createPlanCheckout">
            {{ t('configPage.createCheckout') }}
          </Button>
        </div>
      </div>
    </Card>

    <Card :title="t('configPage.customOrderTitle')">
      <div class="space-y-4">
        <p class="text-sm text-gray-600 dark:text-gray-400">{{ t('configPage.customOrderSubtitle') }}</p>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.company') }}</label>
            <select v-model.number="customOrderForm.id_empresa" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
              <option :value="null">{{ t('configPage.selectCompany') }}</option>
              <option v-for="item in companySubscriptions" :key="`custom-${item.id_empresa}`" :value="item.id_empresa">
                {{ item.empresa_nombre }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.billingCycle') }}</label>
            <select v-model="customOrderForm.billing_cycle" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none">
              <option value="monthly">{{ t('configPage.monthly') }}</option>
              <option value="yearly">{{ t('configPage.yearly') }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.customOrderAmount') }}</label>
            <input v-model.number="customOrderForm.amount_usd" type="number" min="1" step="0.01" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <label class="flex items-center gap-3 text-sm text-gray-700 dark:text-gray-300">
            <input v-model="customOrderForm.generate_payphone_checkout" type="checkbox" class="w-4 h-4" /> {{ t('configPage.customOrderGenerateCheckout') }}
          </label>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.featureOverrides') }}</label>
          <textarea
            v-model="customOrderForm.feature_overrides_text"
            rows="3"
            :placeholder="t('configPage.featureOverridesHint')"
            class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-y"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.customOrderRequirements') }}</label>
          <textarea
            v-model="customOrderForm.custom_requirements"
            rows="3"
            :placeholder="t('configPage.customOrderRequirementsHint')"
            class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-y"
          />
        </div>

        <div class="flex flex-wrap gap-3">
          <Button :loading="creatingCustomOrder" type="button" @click="createCustomOrder">{{ t('configPage.customOrderCreate') }}</Button>
        </div>
      </div>
    </Card>

    <!-- Pending Custom Orders Activation -->
    <Card :title="t('configPage.pendingOrdersTitle')">
      <div class="space-y-4">
        <p class="text-sm text-gray-600 dark:text-gray-400">{{ t('configPage.pendingOrdersSubtitle') }}</p>
        <div v-if="pendingCustomOrders.length === 0" class="text-sm text-gray-500 dark:text-gray-400">{{ t('configPage.noPendingOrders') }}</div>
        <div v-else class="space-y-3">
          <div v-for="order in pendingCustomOrders" :key="`order-${order.id_order}`" class="p-3 border rounded-lg bg-yellow-50 dark:bg-yellow-900/20 dark:border-yellow-700">
            <div class="flex justify-between items-start gap-4">
              <div>
                <p class="font-medium text-sm text-gray-900 dark:text-white">{{ order.empresa_nombre }}</p>
                <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">{{ t('configPage.customOrderLabel') }}: {{ order.order_number }}</p>
                <p class="text-xs text-gray-600 dark:text-gray-400">Total: {{ order.amount }} {{ order.currency }}</p>
              </div>
              <Button
                :loading="activatingOrder"
                size="sm"
                type="button"
                :disabled="!order.id_pago"
                @click="order.id_pago && activateCustomOrder(order.id_pago)"
              >
                {{ t('configPage.activateOrder') }}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Card>

    <Card :title="t('configPage.gatewayTitle')">
      <div v-if="loadingGateways" class="text-sm text-gray-500 dark:text-gray-400">{{ t('common.loading') }}</div>
      <div v-else class="space-y-4">
        <label class="flex items-center gap-3 text-sm text-gray-700 dark:text-gray-300">
          <input v-model="payphoneForm.enabled" type="checkbox" class="w-4 h-4" /> {{ t('configPage.gatewayPayphoneEnabled') }}
        </label>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{{ t('configPage.gatewayEndpoint') }}</label>
            <input v-model="payphoneForm.endpoint_url" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Store ID</label>
            <input v-model="payphoneForm.store_id" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Token / Secret</label>
            <input v-model="payphoneForm.secret" type="password" :placeholder="t('configPage.gatewaySecretPlaceholder')" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Public Key (opcional)</label>
            <input v-model="payphoneForm.public_key" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Return URL</label>
            <input v-model="payphoneForm.return_url" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Cancel URL</label>
            <input v-model="payphoneForm.cancel_url" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Webhook Token</label>
            <input v-model="payphoneForm.webhook_token" type="password" :placeholder="t('configPage.gatewayWebhookTokenPlaceholder')" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
            <p class="text-xs text-gray-500 mt-1" v-if="payphoneForm.has_webhook_token">{{ t('configPage.gatewayWebhookTokenConfigured') }}</p>
          </div>
        </div>

        <p class="text-xs text-gray-500 dark:text-gray-400">{{ t('configPage.gatewayHint') }}</p>

        <div>
          <Button :loading="savingGateway" type="button" @click="savePayphoneConfig">{{ t('configPage.gatewaySave') }}</Button>
        </div>
      </div>
    </Card>

    <Card :title="t('configPage.backupTitle')">
      <div class="flex flex-wrap gap-3">
        <Button @click="downloadBackup">
          <Download :size="16" class="mr-2" /> {{ t('configPage.downloadUsersBackup') }}
        </Button>
        <label class="inline-flex items-center px-4 py-2 rounded-xl border cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 text-sm font-medium">
          <Upload :size="16" class="mr-2" /> {{ t('configPage.restoreBackup') }}
          <input type="file" accept="application/json" class="hidden" @change="handleRestore" />
        </label>
      </div>
      <p class="text-xs text-gray-500 dark:text-gray-400 mt-3">{{ t('configPage.restoreWarning') }}</p>
    </Card>

    <div class="flex justify-end">
      <Button :loading="saving || restoring" @click="saveSettings">{{ t('configPage.saveSettings') }}</Button>
    </div>
  </div>
</template>
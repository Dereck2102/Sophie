<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { CheckCircle, Download, Upload } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import ImageUpload from '../components/ui/ImageUpload.vue'
import api from '../services/api'
import type { AuthChannelsStatus, BackupUsuariosPayload, ConfiguracionSistema } from '../types'

const loading = ref(true)
const saving = ref(false)
const restoring = ref(false)
const checkingChannels = ref(false)
const testingEmail = ref(false)
const testingSms = ref(false)
const success = ref<string | null>(null)
const error = ref<string | null>(null)

const channelStatus = ref<AuthChannelsStatus | null>(null)
const testEmail = ref('')
const testPhone = ref('')

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
    error.value = err.response?.data?.detail ?? 'No se pudo cargar la configuración'
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
    success.value = 'Configuración guardada correctamente'
    await loadChannelStatus()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo guardar la configuración'
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
    error.value = err.response?.data?.detail ?? 'No se pudo enviar correo de prueba'
  } finally {
    testingEmail.value = false
  }
}

async function runSmsTest(): Promise<void> {
  if (!testPhone.value.trim()) {
    error.value = 'Ingresa un número para probar SMS'
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
    error.value = err.response?.data?.detail ?? 'No se pudo enviar SMS de prueba'
  } finally {
    testingSms.value = false
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
    success.value = 'Backup descargado correctamente'
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo descargar el backup'
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
    success.value = 'Backup restaurado correctamente'
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo restaurar el backup'
  } finally {
    restoring.value = false
    input.value = ''
  }
}

onMounted(async () => {
  await loadSettings()
  await loadChannelStatus()
})
</script>

<template>
  <div class="space-y-6 max-w-5xl">
    <div>
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Configuración Global</h1>
      <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">Branding, seguridad y continuidad operativa de tu empresa.</p>
    </div>

    <div v-if="success" class="flex items-center gap-2 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-xl text-sm">
      <CheckCircle :size="16" /> {{ success }}
    </div>
    <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
      {{ error }}
    </div>

    <Card title="Identidad y Branding">
      <div v-if="loading" class="text-sm text-gray-500">Cargando...</div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Nombre de la instancia</label>
          <input v-model="form.nombre_instancia" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Nombre de la empresa</label>
          <input v-model="form.nombre_empresa" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">RUC</label>
          <input v-model="form.ruc_empresa" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Logo de la empresa</label>
          <ImageUpload
            v-model="form.logo_empresa_url"
            image-type="profile"
            :target-width="600"
            accept="image/png,image/jpeg,image/webp"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Color primario</label>
          <input v-model="form.color_primario" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Color secundario</label>
          <input v-model="form.color_secundario" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">Pie de reporte / impresión</label>
          <textarea v-model="form.reporte_footer" rows="2" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none" />
        </div>
      </div>
    </Card>

    <Card title="Seguridad del Sistema">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Zona horaria</label>
          <input v-model="form.timezone" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Mercado</label>
          <input v-model="form.market" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Timeout de sesión (min)</label>
          <input v-model.number="form.session_timeout_minutes" type="number" min="5" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Máx. intentos de login</label>
          <input v-model.number="form.max_login_attempts" type="number" min="1" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <label class="flex items-center gap-3 text-sm text-gray-700">
          <input v-model="form.require_mfa_global" type="checkbox" class="w-4 h-4" /> Requerir MFA globalmente
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

    <Card title="Estado de Canales de Autenticación">
      <div class="space-y-4">
        <div v-if="checkingChannels" class="text-sm text-gray-500">Verificando estado de canales...</div>
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
            <Button :loading="testingEmail" type="button" @click="runEmailTest">Enviar correo de prueba</Button>
          </div>

          <div class="space-y-2">
            <label class="block text-sm font-medium text-gray-700">Probar SMS</label>
            <input
              v-model="testPhone"
              type="text"
              placeholder="+593..."
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
            <Button :loading="testingSms" type="button" @click="runSmsTest">Enviar SMS de prueba</Button>
          </div>
        </div>
      </div>
    </Card>

    <Card title="Parámetros Financieros Globales">
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

    <Card title="Continuidad y Respaldo">
      <div class="flex flex-wrap gap-3">
        <Button @click="downloadBackup">
          <Download :size="16" class="mr-2" /> Descargar backup de usuarios
        </Button>
        <label class="inline-flex items-center px-4 py-2 rounded-xl border cursor-pointer hover:bg-gray-50 text-sm font-medium">
          <Upload :size="16" class="mr-2" /> Restaurar backup
          <input type="file" accept="application/json" class="hidden" @change="handleRestore" />
        </label>
      </div>
      <p class="text-xs text-gray-500 mt-3">La restauración reemplaza usuarios y configuración global actual.</p>
    </Card>

    <div class="flex justify-end">
      <Button :loading="saving || restoring" @click="saveSettings">Guardar configuración</Button>
    </div>
  </div>
</template>
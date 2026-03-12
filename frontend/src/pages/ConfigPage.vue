<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { CheckCircle, Download, Upload } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import api from '../services/api'
import type { BackupUsuariosPayload, ConfiguracionSistema } from '../types'

const loading = ref(true)
const saving = ref(false)
const restoring = ref(false)
const success = ref<string | null>(null)
const error = ref<string | null>(null)

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
  max_login_attempts: 5,
  color_primario: '#2563eb',
  color_secundario: '#0f172a',
  reporte_footer: '',
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

async function saveSettings(): Promise<void> {
  saving.value = true
  success.value = null
  error.value = null
  try {
    const { data } = await api.patch<ConfiguracionSistema>('/api/v1/admin/settings', form.value)
    form.value = data
    success.value = 'Configuración guardada correctamente'
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo guardar la configuración'
  } finally {
    saving.value = false
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

onMounted(loadSettings)
</script>

<template>
  <div class="space-y-6 max-w-5xl">
    <div>
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Configuración Global</h1>
      <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">Branding, seguridad y continuidad operativa del entorno ZOHOGESTIO.</p>
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
          <label class="block text-sm font-medium text-gray-700 mb-1">Logo URL / data URL</label>
          <input v-model="form.logo_empresa_url" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
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
          <input v-model="form.email_notifications" type="checkbox" class="w-4 h-4" /> Notificaciones por email
        </label>
        <label class="flex items-center gap-3 text-sm text-gray-700 md:col-span-2">
          <input v-model="form.system_notifications" type="checkbox" class="w-4 h-4" /> Notificaciones del sistema
        </label>
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
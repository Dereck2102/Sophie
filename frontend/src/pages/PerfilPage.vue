<script setup lang="ts">
import { ref, computed } from 'vue'
import { UserCircle, Lock, Bell, CheckCircle, AlertCircle, Users, Package, Settings, ShieldCheck } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import ImageUpload from '../components/ui/ImageUpload.vue'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'
import type { EmailVerificationTokenResponse, RecoveryCodesResponse, Usuario } from '../types'

const auth = useAuthStore()

// Profile form
const profileForm = ref({
  nombre_completo: auth.user?.nombre_completo ?? '',
  email: auth.user?.email ?? '',
  telefono_recuperacion: auth.user?.telefono_recuperacion ?? '',
  foto_perfil_url: auth.user?.foto_perfil_url ?? '',
})
const profileSaving = ref(false)
const profileSuccess = ref(false)
const profileError = ref<string | null>(null)

// Password form
const passwordForm = ref({
  current_password: '',
  new_password: '',
  confirm_password: '',
})
const passwordSaving = ref(false)
const passwordSuccess = ref(false)
const passwordError = ref<string | null>(null)
const verificationToken = ref('')
const verificationTokenExpires = ref<string | null>(null)
const verificationLoading = ref(false)
const verificationError = ref<string | null>(null)
const verificationSuccess = ref<string | null>(null)
const recoveryCodes = ref<string[]>([])
const recoveryCodesLoading = ref(false)
const recoveryCodesError = ref<string | null>(null)
const recoveryCodesGeneratedAt = ref<string | null>(null)
const recoveryPassword = ref('')

const roleLabels: Record<string, string> = {
  superadmin: 'Superadministrador',
  ejecutivo: 'Ejecutivo',
  administrativo_contable: 'Administrativo Contable',
  tecnico: 'Técnico',
}

const userInitials = computed(() => {
  const name = auth.user?.nombre_completo ?? auth.user?.username ?? ''
  return name
    .split(' ')
    .slice(0, 2)
    .map((n) => n[0])
    .join('')
    .toUpperCase()
})

const adminShortcuts = [
  { label: 'Gestionar usuarios', route: '/usuarios', icon: Users, description: 'Editar roles, activar o eliminar cuentas' },
  { label: 'Controlar inventario', route: '/compras', icon: Package, description: 'Ajustar stock, costos y catálogo' },
  { label: 'Configuración', route: '/configuracion', icon: Settings, description: 'Parámetros globales del sistema' },
  { label: 'Auditoría', route: '/auditoria', icon: ShieldCheck, description: 'Revisar trazabilidad y actividad global' },
]

const isAdminArea = computed(() => ['superadmin'].includes(auth.user?.rol ?? ''))
const visibleAdminShortcuts = computed(() => adminShortcuts.filter((shortcut) => auth.user?.rol === 'superadmin' || shortcut.route !== '/auditoria'))

async function saveProfile(): Promise<void> {
  profileSaving.value = true
  profileError.value = null
  profileSuccess.value = false
  try {
    const { data } = await api.patch<Usuario>('/api/v1/usuarios/me', {
      nombre_completo: profileForm.value.nombre_completo || undefined,
      email: profileForm.value.email,
      telefono_recuperacion: profileForm.value.telefono_recuperacion || undefined,
      foto_perfil_url: profileForm.value.foto_perfil_url || undefined,
    })
    auth.user = data
    profileSuccess.value = true
    setTimeout(() => { profileSuccess.value = false }, 3000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    profileError.value = err.response?.data?.detail ?? 'Error al guardar perfil'
  } finally {
    profileSaving.value = false
  }
}

async function changePassword(): Promise<void> {
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    passwordError.value = 'Las contraseñas nuevas no coinciden'
    return
  }
  passwordSaving.value = true
  passwordError.value = null
  passwordSuccess.value = false
  try {
    await api.patch('/api/v1/usuarios/me', {
      current_password: passwordForm.value.current_password,
      new_password: passwordForm.value.new_password,
    })
    passwordSuccess.value = true
    passwordForm.value = { current_password: '', new_password: '', confirm_password: '' }
    setTimeout(() => { passwordSuccess.value = false }, 3000)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    passwordError.value = err.response?.data?.detail ?? 'Error al cambiar contraseña'
  } finally {
    passwordSaving.value = false
  }
}

async function requestVerificationToken(): Promise<void> {
  verificationLoading.value = true
  verificationError.value = null
  verificationSuccess.value = null
  try {
    const { data } = await api.post<EmailVerificationTokenResponse>('/api/v1/auth/email/verification-token')
    verificationToken.value = data.token
    verificationTokenExpires.value = data.expires_at
    verificationSuccess.value = 'Token generado correctamente'
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    verificationError.value = err.response?.data?.detail ?? 'No se pudo generar el token'
  } finally {
    verificationLoading.value = false
  }
}

async function verifyEmailToken(): Promise<void> {
  if (!verificationToken.value) {
    verificationError.value = 'Ingresa un token de verificación'
    return
  }
  verificationLoading.value = true
  verificationError.value = null
  verificationSuccess.value = null
  try {
    await api.post('/api/v1/auth/email/verify', { token: verificationToken.value })
    await auth.fetchMe()
    profileForm.value.email = auth.user?.email ?? profileForm.value.email
    verificationSuccess.value = 'Correo verificado correctamente'
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    verificationError.value = err.response?.data?.detail ?? 'No se pudo verificar el token'
  } finally {
    verificationLoading.value = false
  }
}

async function rotateRecoveryCodes(): Promise<void> {
  if (!recoveryPassword.value) {
    recoveryCodesError.value = 'Ingresa tu contraseña actual para generar códigos de recuperación'
    return
  }
  recoveryCodesLoading.value = true
  recoveryCodesError.value = null
  try {
    const { data } = await api.post<RecoveryCodesResponse>('/api/v1/auth/mfa/recovery-codes/rotate', {
      current_password: recoveryPassword.value,
    })
    recoveryCodes.value = data.codes
    recoveryCodesGeneratedAt.value = data.generated_at
    recoveryPassword.value = ''
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    recoveryCodesError.value = err.response?.data?.detail ?? 'No se pudieron generar los códigos'
  } finally {
    recoveryCodesLoading.value = false
  }
}
</script>

<template>
  <div class="space-y-6 max-w-3xl px-1 sm:px-0">
    <!-- Header -->
    <div class="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:gap-4">
      <img
        v-if="auth.user?.foto_perfil_url"
        :src="auth.user.foto_perfil_url"
        alt="Foto de perfil"
        class="h-16 w-16 rounded-2xl object-cover"
      />
      <div v-else class="h-16 w-16 rounded-2xl bg-blue-600 flex items-center justify-center text-white text-xl font-bold">
        {{ userInitials }}
      </div>
      <div class="min-w-0">
        <h1 class="truncate text-2xl font-bold text-gray-900">
          {{ auth.user?.nombre_completo ?? auth.user?.username }}
        </h1>
        <p class="break-words text-gray-500 text-sm">
          {{ roleLabels[auth.user?.rol ?? ''] ?? auth.user?.rol }} ·
          {{ auth.user?.email }}
        </p>
      </div>
    </div>

    <!-- Profile Information -->
    <Card title="Información del Perfil">
      <form @submit.prevent="saveProfile" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Usuario</label>
            <input
              :value="auth.user?.username"
              type="text"
              disabled
              class="w-full px-3 py-2 text-sm border rounded-lg bg-gray-50 text-gray-400 cursor-not-allowed"
            />
            <p class="text-xs text-gray-400 mt-1">El nombre de usuario no se puede cambiar</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Rol</label>
            <input
              :value="roleLabels[auth.user?.rol ?? ''] ?? auth.user?.rol"
              type="text"
              disabled
              class="w-full px-3 py-2 text-sm border rounded-lg bg-gray-50 text-gray-400 cursor-not-allowed"
            />
          </div>
          <div class="sm:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Nombre Completo</label>
            <input
              v-model="profileForm.nombre_completo"
              type="text"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="Tu nombre completo"
            />
          </div>
          <div class="sm:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              v-model="profileForm.email"
              type="email"
              required
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div class="sm:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Teléfono de recuperación</label>
            <input
              v-model="profileForm.telefono_recuperacion"
              type="tel"
              inputmode="tel"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="+593..."
            />
            <p class="text-xs text-gray-400 mt-1">Se usa para recuperación de cuenta y verificación futura.</p>
          </div>
          <div class="sm:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Foto de Perfil</label>
            <ImageUpload
              v-model="profileForm.foto_perfil_url"
              label="Foto de perfil"
              image-type="profile"
              :target-width="360"
              preview-class="w-24 h-24 sm:w-32 sm:h-32 rounded-xl object-cover"
              dropzone-class="min-h-[96px] sm:min-h-[110px]"
            />
          </div>
        </div>

        <div v-if="profileSuccess" class="flex items-center gap-2 text-sm text-green-700 bg-green-50 px-3 py-2 rounded-lg">
          <CheckCircle :size="16" />
          Perfil actualizado correctamente
        </div>
        <div v-if="profileError" class="flex items-center gap-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          <AlertCircle :size="16" />
          {{ profileError }}
        </div>

        <div class="flex justify-end">
          <Button type="submit" :loading="profileSaving">
            <UserCircle :size="16" class="mr-2" />
            Guardar Perfil
          </Button>
        </div>
      </form>
    </Card>

    <!-- Change Password -->
    <Card title="Cambiar Contraseña">
      <form @submit.prevent="changePassword" class="space-y-4">
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Contraseña Actual *</label>
            <input
              v-model="passwordForm.current_password"
              type="password"
              required
              autocomplete="current-password"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Nueva Contraseña *</label>
              <input
                v-model="passwordForm.new_password"
                type="password"
                required
                minlength="8"
                autocomplete="new-password"
                class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              />
              <p class="text-xs text-gray-400 mt-1">Mínimo 8 caracteres</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Confirmar Contraseña *</label>
              <input
                v-model="passwordForm.confirm_password"
                type="password"
                required
                minlength="8"
                autocomplete="new-password"
                class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
          </div>
        </div>

        <div v-if="passwordSuccess" class="flex items-center gap-2 text-sm text-green-700 bg-green-50 px-3 py-2 rounded-lg">
          <CheckCircle :size="16" />
          Contraseña cambiada correctamente
        </div>
        <div v-if="passwordError" class="flex items-center gap-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          <AlertCircle :size="16" />
          {{ passwordError }}
        </div>

        <div class="flex justify-end">
          <Button type="submit" :loading="passwordSaving">
            <Lock :size="16" class="mr-2" />
            Cambiar Contraseña
          </Button>
        </div>
      </form>
    </Card>

    <!-- Account Info -->
    <Card title="Información de la Cuenta">
      <div class="space-y-3 text-sm">
        <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between py-2 border-b border-gray-50">
          <span class="text-gray-500">Miembro desde</span>
          <span class="font-medium text-gray-800">
            {{ auth.user?.fecha_creacion ? new Date(auth.user.fecha_creacion).toLocaleDateString('es-PE', { year: 'numeric', month: 'long', day: 'numeric' }) : '—' }}
          </span>
        </div>
        <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between py-2 border-b border-gray-50">
          <span class="text-gray-500">Autenticación de dos factores (MFA)</span>
          <span :class="auth.user?.mfa_habilitado ? 'text-green-600 font-medium' : 'text-gray-400'">
            {{ auth.user?.mfa_habilitado ? 'Activado' : 'Desactivado' }}
          </span>
        </div>
        <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between py-2 border-b border-gray-50">
          <span class="text-gray-500">Teléfono recuperación</span>
          <span :class="auth.user?.telefono_recuperacion ? 'text-green-600 font-medium' : 'text-gray-400'">
            {{ auth.user?.telefono_recuperacion ? auth.user.telefono_recuperacion : 'No configurado' }}
          </span>
        </div>
        <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between py-2">
          <span class="text-gray-500">Estado de cuenta</span>
          <span :class="auth.user?.activo ? 'text-green-600 font-medium' : 'text-red-500 font-medium'">
            {{ auth.user?.activo ? 'Activa' : 'Inactiva' }}
          </span>
        </div>
      </div>
      <div v-if="!auth.user?.mfa_habilitado" class="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
        <Bell class="text-amber-500 shrink-0 mt-0.5" :size="16" />
        <div>
          <p class="text-sm font-medium text-amber-800">Aumenta la seguridad de tu cuenta</p>
          <p class="text-xs text-amber-700 mt-1">
            Activa la autenticación de dos factores (MFA) desde el endpoint <code class="bg-amber-100 px-1 rounded">/api/v1/auth/mfa/setup</code> para proteger mejor tu cuenta.
          </p>
        </div>
      </div>

      <div v-if="!auth.user?.email_verificado" class="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg space-y-3">
        <div class="flex items-start gap-2 text-blue-800">
          <ShieldCheck :size="16" class="mt-0.5" />
          <div>
            <p class="text-sm font-medium">Verificación de correo pendiente</p>
            <p class="text-xs text-blue-700">Genera un token y confírmalo para validar tu correo en la plataforma.</p>
          </div>
        </div>
        <div class="flex flex-col sm:flex-row sm:flex-wrap sm:items-center gap-2">
          <Button variant="secondary" :loading="verificationLoading" @click="requestVerificationToken">
            Generar token
          </Button>
          <input
            v-model="verificationToken"
            type="text"
            placeholder="Pega o escribe token"
            class="w-full sm:w-auto px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none sm:min-w-[250px]"
          />
          <Button :loading="verificationLoading" @click="verifyEmailToken">Verificar</Button>
        </div>
        <p v-if="verificationTokenExpires" class="text-xs text-blue-700">
          Expira: {{ new Date(verificationTokenExpires).toLocaleString('es-EC') }}
        </p>
        <p v-if="verificationSuccess" class="text-xs text-green-700 bg-green-50 border border-green-200 rounded px-2 py-1">{{ verificationSuccess }}</p>
        <p v-if="verificationError" class="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1">{{ verificationError }}</p>
      </div>
      <div v-else class="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
        Correo verificado correctamente.
      </div>

      <div v-if="auth.user?.mfa_habilitado" class="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-3">
        <div>
          <p class="text-sm font-medium text-slate-800">Códigos de recuperación MFA</p>
          <p class="text-xs text-slate-600 mt-1">Guárdalos offline. Cada código sirve una sola vez cuando no tengas tu app TOTP.</p>
        </div>
        <div class="flex flex-col sm:flex-row gap-2">
          <input
            v-model="recoveryPassword"
            type="password"
            autocomplete="current-password"
            placeholder="Confirma tu contraseña actual"
            class="w-full sm:w-auto sm:min-w-[280px] px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
          />
          <Button :loading="recoveryCodesLoading" @click="rotateRecoveryCodes">Generar códigos</Button>
        </div>
        <p v-if="recoveryCodesError" class="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1">{{ recoveryCodesError }}</p>
        <div v-if="recoveryCodes.length > 0" class="bg-white border border-slate-200 rounded-lg p-3">
          <p class="text-xs text-slate-500 mb-2">Generados: {{ recoveryCodesGeneratedAt ? new Date(recoveryCodesGeneratedAt).toLocaleString('es-EC') : 'ahora' }}</p>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <code v-for="code in recoveryCodes" :key="code" class="px-2 py-1 rounded bg-slate-100 text-slate-800 text-xs text-center">{{ code }}</code>
          </div>
        </div>
      </div>
    </Card>

    <Card v-if="isAdminArea" title="Herramientas de Administración">
      <div class="grid gap-3 sm:grid-cols-3">
        <router-link
          v-for="shortcut in visibleAdminShortcuts"
          :key="shortcut.route"
          :to="shortcut.route"
          class="rounded-xl border border-gray-200 px-4 py-3 hover:border-blue-300 hover:bg-blue-50 transition-colors"
        >
          <component :is="shortcut.icon" :size="18" class="text-blue-600" />
          <p class="mt-3 text-sm font-semibold text-gray-900">{{ shortcut.label }}</p>
          <p class="mt-1 text-xs text-gray-500">{{ shortcut.description }}</p>
        </router-link>
      </div>
    </Card>
  </div>
</template>

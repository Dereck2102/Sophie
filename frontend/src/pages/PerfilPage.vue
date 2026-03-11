<script setup lang="ts">
import { ref, computed } from 'vue'
import { UserCircle, Lock, Bell, CheckCircle, AlertCircle } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'
import type { Usuario } from '../types'

const auth = useAuthStore()

// Profile form
const profileForm = ref({
  nombre_completo: auth.user?.nombre_completo ?? '',
  email: auth.user?.email ?? '',
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

const roleLabels: Record<string, string> = {
  admin: 'Administrador',
  vendedor: 'Vendedor',
  tecnico_taller: 'Técnico Taller',
  tecnico_it: 'Técnico IT',
  comprador: 'Comprador',
  desarrollador: 'Desarrollador',
  consultor_senior: 'Consultor Senior',
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

async function saveProfile(): Promise<void> {
  profileSaving.value = true
  profileError.value = null
  profileSuccess.value = false
  try {
    const { data } = await api.patch<Usuario>('/api/v1/usuarios/me', {
      nombre_completo: profileForm.value.nombre_completo || undefined,
      email: profileForm.value.email,
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
</script>

<template>
  <div class="space-y-6 max-w-3xl">
    <!-- Header -->
    <div class="flex items-center gap-4">
      <div class="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center text-white text-xl font-bold">
        {{ userInitials }}
      </div>
      <div>
        <h1 class="text-2xl font-bold text-gray-900">
          {{ auth.user?.nombre_completo ?? auth.user?.username }}
        </h1>
        <p class="text-gray-500 text-sm">
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
        <div class="flex justify-between py-2 border-b border-gray-50">
          <span class="text-gray-500">Miembro desde</span>
          <span class="font-medium text-gray-800">
            {{ auth.user?.fecha_creacion ? new Date(auth.user.fecha_creacion).toLocaleDateString('es-PE', { year: 'numeric', month: 'long', day: 'numeric' }) : '—' }}
          </span>
        </div>
        <div class="flex justify-between py-2 border-b border-gray-50">
          <span class="text-gray-500">Autenticación de dos factores (MFA)</span>
          <span :class="auth.user?.mfa_habilitado ? 'text-green-600 font-medium' : 'text-gray-400'">
            {{ auth.user?.mfa_habilitado ? 'Activado' : 'Desactivado' }}
          </span>
        </div>
        <div class="flex justify-between py-2">
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
    </Card>
  </div>
</template>

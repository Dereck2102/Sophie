<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from '../components/ui/Button.vue'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'
import type { LoginRequest, PasswordRecoveryConfirmRequest, PasswordRecoveryRequest } from '../types'

const auth = useAuthStore()
const router = useRouter()

const form = ref<LoginRequest>({ username: '', password: '' })
const mfaCode = ref('')
const recoveryCode = ref('')
const showMfa = ref(false)
const useRecoveryCode = ref(false)
const showRecovery = ref(false)
const recoveryRequest = ref<PasswordRecoveryRequest>({ identifier: '' })
const recoveryConfirm = ref<PasswordRecoveryConfirmRequest>({ token: '', new_password: '' })
const recoveryLoading = ref(false)
const recoveryMessage = ref<string | null>(null)
const recoveryError = ref<string | null>(null)

onMounted(() => {
  if (auth.isAuthenticated) router.replace('/')
})

async function handleSubmit(): Promise<void> {
  const payload: LoginRequest = { ...form.value }
  if (showMfa.value) {
    if (useRecoveryCode.value) payload.recovery_code = recoveryCode.value
    else payload.mfa_code = mfaCode.value
  }

  const success = await auth.login(payload)
  if (auth.mfaRequired && !showMfa.value) {
    showMfa.value = true
    return
  }
  if (success) router.replace('/')
}

async function resendMfaByEmail(): Promise<void> {
  mfaCode.value = ''
  recoveryCode.value = ''
  useRecoveryCode.value = false
  await auth.login({ username: form.value.username, password: form.value.password })
}

async function requestRecoveryToken(): Promise<void> {
  recoveryLoading.value = true
  recoveryError.value = null
  recoveryMessage.value = null
  try {
    const { data } = await api.post<{ detail: string; recovery_token?: string | null }>(
      '/api/v1/auth/password-recovery/request',
      recoveryRequest.value,
    )
    recoveryMessage.value = data.recovery_token
      ? `${data.detail} Token temporal: ${data.recovery_token}`
      : data.detail
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    recoveryError.value = err.response?.data?.detail ?? 'No se pudo solicitar recuperación'
  } finally {
    recoveryLoading.value = false
  }
}

async function confirmRecoveryPassword(): Promise<void> {
  recoveryLoading.value = true
  recoveryError.value = null
  recoveryMessage.value = null
  try {
    const { data } = await api.post<{ detail: string }>('/api/v1/auth/password-recovery/confirm', recoveryConfirm.value)
    recoveryMessage.value = data.detail
    recoveryConfirm.value.new_password = ''
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    recoveryError.value = err.response?.data?.detail ?? 'No se pudo actualizar la contraseña'
  } finally {
    recoveryLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-blue-700 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-14 h-14 bg-blue-600 rounded-2xl mb-4">
          <span class="text-white font-bold text-2xl">S</span>
        </div>
        <h1 class="text-2xl font-bold text-gray-900">SOPHIE</h1>
        <p class="text-gray-500 text-sm mt-1">Sistema ERP/CRM — Big Solutions</p>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div v-if="!showMfa">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Usuario</label>
            <input
              v-model="form.username"
              type="text"
              required
              autocomplete="username"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
              placeholder="superadmin"
            />
          </div>
          <div class="mt-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
            <input
              v-model="form.password"
              type="password"
              required
              autocomplete="current-password"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
              placeholder="••••••••"
            />
          </div>
        </div>

        <!-- MFA Step -->
        <div v-else>
          <div class="text-center mb-4">
            <div class="w-12 h-12 bg-amber-50 rounded-full flex items-center justify-center mx-auto mb-3">
              <svg class="w-6 h-6 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <p class="text-sm text-gray-600">
              {{ auth.mfaChannel === 'email' ? 'Ingresa el código enviado a tu correo' : 'Ingresa el código de tu aplicación autenticadora' }}
            </p>
            <p v-if="auth.mfaDestination" class="text-xs text-gray-500 mt-1">Destino: {{ auth.mfaDestination }}</p>
            <p v-if="auth.mfaDebugCode" class="text-xs text-amber-700 mt-1">Código temporal (DEBUG): {{ auth.mfaDebugCode }}</p>
          </div>
          <input
            v-model="mfaCode"
            v-if="!useRecoveryCode"
            type="text"
            inputmode="numeric"
            pattern="[0-9]{6}"
            maxlength="6"
            autofocus
            class="w-full px-4 py-3 border border-gray-300 rounded-lg text-center text-2xl font-mono tracking-widest focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
            placeholder="000000"
          />
          <input
            v-model="recoveryCode"
            v-else
            type="text"
            class="w-full px-4 py-3 border border-gray-300 rounded-lg text-center text-lg font-mono tracking-widest focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
            placeholder="RECOVERY-CODE"
          />
          <button type="button" @click="useRecoveryCode = !useRecoveryCode" class="mt-2 text-sm text-blue-600 hover:underline w-full text-center">
            {{ useRecoveryCode ? 'Usar código TOTP' : 'Usar código de recuperación' }}
          </button>
          <button
            v-if="auth.mfaChannel === 'email'"
            type="button"
            @click="resendMfaByEmail"
            class="mt-1 text-sm text-blue-600 hover:underline w-full text-center"
          >
            Reenviar código por correo
          </button>
          <button type="button" @click="showMfa = false" class="mt-2 text-sm text-blue-600 hover:underline w-full text-center">
            ← Volver
          </button>
        </div>

        <!-- Error -->
        <p v-if="auth.error" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
          {{ auth.error }}
        </p>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          :loading="auth.loading"
          class="w-full mt-2"
        >
          {{ showMfa ? 'Verificar MFA' : 'Iniciar Sesión' }}
        </Button>

        <button type="button" class="w-full text-sm text-blue-600 hover:underline" @click="showRecovery = !showRecovery">
          {{ showRecovery ? 'Ocultar recuperación de contraseña' : '¿Olvidaste tu contraseña?' }}
        </button>

        <div v-if="showRecovery" class="mt-2 rounded-xl border border-gray-200 bg-gray-50 p-4 space-y-3">
          <p class="text-sm font-medium text-gray-700">Recuperación de cuenta</p>
          <input
            v-model="recoveryRequest.identifier"
            type="text"
            placeholder="Usuario, correo o teléfono"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
          />
          <Button type="button" :loading="recoveryLoading" class="w-full" @click="requestRecoveryToken">Solicitar token</Button>
          <input
            v-model="recoveryConfirm.token"
            type="text"
            placeholder="Token de recuperación"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
          />
          <input
            v-model="recoveryConfirm.new_password"
            type="password"
            placeholder="Nueva contraseña"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
          />
          <Button type="button" :loading="recoveryLoading" class="w-full" @click="confirmRecoveryPassword">Confirmar cambio</Button>
          <p v-if="recoveryMessage" class="text-xs text-green-700 bg-green-50 border border-green-200 rounded px-2 py-1">{{ recoveryMessage }}</p>
          <p v-if="recoveryError" class="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-2 py-1">{{ recoveryError }}</p>
        </div>
      </form>
    </div>
  </div>
</template>

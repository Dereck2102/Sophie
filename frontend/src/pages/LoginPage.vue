<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from '../components/ui/Button.vue'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'
import type { LoginRequest, PasswordRecoveryConfirmRequest, PasswordRecoveryRequest } from '../types'

const auth = useAuthStore()
const router = useRouter()

// ── State ──────────────────────────────────────────────────────────────────
const form = ref<LoginRequest>({ username: '', password: '' })
const twoFaCode = ref('')
const recoveryCode = ref('')
const useRecoveryCode = ref(false)
const showPasswordInput = ref(false)

// Password recovery
const showRecovery = ref(false)
const recoveryStep = ref<'request' | 'confirm'>('request')
const recoveryRequest = ref<PasswordRecoveryRequest>({ identifier: '' })
const recoveryConfirm = ref<PasswordRecoveryConfirmRequest>({ token: '', new_password: '' })
const recoveryLoading = ref(false)
const recoveryMessage = ref<string | null>(null)
const recoveryError = ref<string | null>(null)

onMounted(() => {
  if (auth.isAuthenticated) router.replace('/')
})

// ── Helpers ────────────────────────────────────────────────────────────────
const step = ref<'credentials' | 'code'>('credentials')

async function handleSubmit(): Promise<void> {
  const payload: LoginRequest = { ...form.value }

  if (step.value === 'code') {
    if (useRecoveryCode.value) payload.recovery_code = recoveryCode.value
    else payload.mfa_code = twoFaCode.value
  }

  const success = await auth.login(payload)

  if (auth.mfaRequired && step.value === 'credentials') {
    step.value = 'code'
    return
  }
  if (success) router.replace('/')
}

async function resendCode(): Promise<void> {
  twoFaCode.value = ''
  recoveryCode.value = ''
  useRecoveryCode.value = false
  await auth.login({ username: form.value.username, password: form.value.password })
}

function goBack(): void {
  step.value = 'credentials'
  auth.error = null
  twoFaCode.value = ''
  recoveryCode.value = ''
  useRecoveryCode.value = false
}

// ── Password Recovery ──────────────────────────────────────────────────────
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
      ? `Token temporal: ${data.recovery_token}`
      : data.detail
    recoveryStep.value = 'confirm'
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
    recoveryStep.value = 'request'
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    recoveryError.value = err.response?.data?.detail ?? 'No se pudo actualizar la contraseña'
  } finally {
    recoveryLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-blue-900 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">

      <!-- Header band -->
      <div class="bg-gradient-to-r from-blue-700 to-blue-600 px-8 py-6 text-center">
        <div class="inline-flex items-center justify-center w-12 h-12 bg-white/20 rounded-xl mb-3">
          <span class="text-white font-bold text-xl">S</span>
        </div>
        <h1 class="text-xl font-bold text-white tracking-wide">SOPHIE</h1>
        <p class="text-blue-200 text-xs mt-0.5">ERP</p>
      </div>

      <!-- Step indicator -->
      <div class="flex items-center px-8 pt-5 pb-1 gap-2">
        <div
          class="flex items-center gap-1.5 text-xs font-medium"
          :class="step === 'credentials' ? 'text-blue-700' : 'text-gray-400'"
        >
          <span
            class="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold"
            :class="step === 'credentials' ? 'bg-blue-700 text-white' : 'bg-gray-200 text-gray-500'"
          >1</span>
          Credenciales
        </div>
        <div class="flex-1 h-px" :class="step === 'code' ? 'bg-blue-600' : 'bg-gray-200'"></div>
        <div
          class="flex items-center gap-1.5 text-xs font-medium"
          :class="step === 'code' ? 'text-blue-700' : 'text-gray-400'"
        >
          <span
            class="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold"
            :class="step === 'code' ? 'bg-blue-700 text-white' : 'bg-gray-200 text-gray-500'"
          >2</span>
          Verificación
        </div>
      </div>

      <form @submit.prevent="handleSubmit" class="px-8 pt-4 pb-8 space-y-4">

        <!-- ── Step 1: Credentials ── -->
        <template v-if="step === 'credentials'">
          <div>
            <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Usuario</label>
            <input
              v-model="form.username"
              type="text"
              required
              autocomplete="username"
              class="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition bg-gray-50 focus:bg-white"
              placeholder="nombre de usuario"
            />
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">Contraseña</label>
            <div class="relative">
              <input
                v-model="form.password"
                :type="showPasswordInput ? 'text' : 'password'"
                required
                autocomplete="current-password"
                class="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition bg-gray-50 focus:bg-white pr-10"
                placeholder="••••••••"
              />
              <button
                type="button"
                @click="showPasswordInput = !showPasswordInput"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                tabindex="-1"
              >
                <svg v-if="!showPasswordInput" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                </svg>
              </button>
            </div>
          </div>
        </template>

        <!-- ── Step 2: 2FA Code ── -->
        <template v-else>
          <div class="text-center py-2">
            <!-- Icon -->
            <div class="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
              <svg class="w-7 h-7 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
              </svg>
            </div>

            <p v-if="!useRecoveryCode" class="text-sm font-medium text-gray-700">Código de verificación</p>
            <p v-else class="text-sm font-medium text-gray-700">Código de recuperación</p>

            <!-- Destinations sent to -->
            <div v-if="!useRecoveryCode" class="mt-2 space-y-0.5">
              <p v-if="auth.mfaDestination" class="text-xs text-gray-500 flex items-center justify-center gap-1">
                <span>✉</span>
                <span>{{ auth.mfaDestination }}</span>
              </p>
              <p v-if="auth.mfaPhoneDestination" class="text-xs text-gray-500 flex items-center justify-center gap-1">
                <span>📱</span>
                <span>{{ auth.mfaPhoneDestination }}</span>
              </p>
            </div>

            <!-- Debug code pill -->
            <div v-if="auth.mfaDebugCode && !useRecoveryCode" class="mt-2 inline-flex items-center gap-1.5 bg-amber-50 border border-amber-200 rounded-lg px-3 py-1">
              <svg class="w-3.5 h-3.5 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
              </svg>
              <span class="text-xs font-mono font-semibold text-amber-700">{{ auth.mfaDebugCode }}</span>
              <span class="text-xs text-amber-600">(dev)</span>
            </div>
          </div>

          <!-- Code input -->
          <div v-if="!useRecoveryCode">
            <input
              v-model="twoFaCode"
              type="text"
              inputmode="numeric"
              pattern="[0-9]{6}"
              maxlength="6"
              autofocus
              class="w-full px-4 py-4 border-2 border-gray-200 rounded-xl text-center text-3xl font-mono tracking-[0.5em] focus:ring-0 focus:border-blue-500 outline-none transition bg-gray-50 focus:bg-white placeholder-gray-300"
              placeholder="––––––"
            />
            <p class="text-center text-xs text-gray-400 mt-1.5">Ingresa los 6 dígitos recibidos</p>
          </div>
          <div v-else>
            <input
              v-model="recoveryCode"
              type="text"
              autofocus
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-center text-sm font-mono tracking-widest focus:ring-0 focus:border-blue-500 outline-none transition bg-gray-50 focus:bg-white"
              placeholder="XXXX-XXXX-XXXX"
            />
            <p class="text-center text-xs text-gray-400 mt-1.5">Ingresa uno de tus códigos de recuperación guardados</p>
          </div>

          <!-- Action links -->
          <div class="flex flex-col items-center gap-1 pt-1">
            <button
              v-if="auth.mfaChannel?.includes('email') || auth.mfaChannel?.includes('sms')"
              type="button"
              @click="resendCode"
              class="text-xs text-blue-600 hover:text-blue-800 hover:underline"
            >
              Reenviar código
            </button>
            <button
              type="button"
              @click="useRecoveryCode = !useRecoveryCode; twoFaCode = ''; recoveryCode = ''"
              class="text-xs text-gray-500 hover:text-gray-700 hover:underline"
            >
              {{ useRecoveryCode ? '← Volver al código de verificación' : '¿No tienes acceso? Usar código de recuperación' }}
            </button>
            <button type="button" @click="goBack" class="text-xs text-gray-400 hover:text-gray-600 hover:underline">
              ← Cambiar credenciales
            </button>
          </div>
        </template>

        <!-- ── Error ── -->
        <div v-if="auth.error" class="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl px-3 py-2">
          <svg class="w-4 h-4 text-red-500 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
          </svg>
          <p class="text-sm text-red-700">{{ auth.error }}</p>
        </div>

        <!-- ── Submit ── -->
        <Button
          type="submit"
          variant="primary"
          size="lg"
          :loading="auth.loading"
          class="w-full"
        >
          {{ step === 'credentials' ? 'Continuar' : (useRecoveryCode ? 'Ingresar con código de recuperación' : 'Verificar e ingresar') }}
        </Button>

        <!-- ── Password Recovery toggle ── -->
        <div class="text-center">
          <button
            type="button"
            class="text-xs text-gray-400 hover:text-blue-600 hover:underline transition-colors"
            @click="showRecovery = !showRecovery; recoveryMessage = null; recoveryError = null"
          >
            {{ showRecovery ? 'Ocultar recuperación' : '¿Olvidaste tu contraseña?' }}
          </button>
        </div>

        <!-- ── Password Recovery panel ── -->
        <Transition name="slide-down">
          <div v-if="showRecovery" class="rounded-xl border border-gray-100 bg-gray-50 p-4 space-y-3">
            <div class="flex items-center justify-between">
              <p class="text-xs font-semibold text-gray-600 uppercase tracking-wider">Recuperar contraseña</p>
              <div class="flex gap-2">
                <button
                  type="button"
                  @click="recoveryStep = 'request'; recoveryMessage = null; recoveryError = null"
                  class="text-xs px-2 py-0.5 rounded-md transition"
                  :class="recoveryStep === 'request' ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-400 hover:text-gray-600'"
                >Solicitar</button>
                <button
                  type="button"
                  @click="recoveryStep = 'confirm'; recoveryMessage = null; recoveryError = null"
                  class="text-xs px-2 py-0.5 rounded-md transition"
                  :class="recoveryStep === 'confirm' ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-400 hover:text-gray-600'"
                >Confirmar</button>
              </div>
            </div>

            <!-- Request step -->
            <template v-if="recoveryStep === 'request'">
              <input
                v-model="recoveryRequest.identifier"
                type="text"
                placeholder="Usuario, correo o teléfono"
                class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-400 outline-none bg-white"
              />
              <Button type="button" size="sm" :loading="recoveryLoading" class="w-full" @click="requestRecoveryToken">
                Enviar token de recuperación
              </Button>
            </template>

            <!-- Confirm step -->
            <template v-else>
              <input
                v-model="recoveryConfirm.token"
                type="text"
                placeholder="Token recibido"
                class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-400 outline-none bg-white font-mono"
              />
              <input
                v-model="recoveryConfirm.new_password"
                type="password"
                placeholder="Nueva contraseña"
                class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-400 outline-none bg-white"
              />
              <Button type="button" size="sm" :loading="recoveryLoading" class="w-full" @click="confirmRecoveryPassword">
                Actualizar contraseña
              </Button>
            </template>

            <p v-if="recoveryMessage" class="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">{{ recoveryMessage }}</p>
            <p v-if="recoveryError" class="text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{{ recoveryError }}</p>
          </div>
        </Transition>

      </form>
    </div>
  </div>
</template>

<style scoped>
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}
.slide-down-enter-to,
.slide-down-leave-from {
  opacity: 1;
  max-height: 500px;
}
</style>


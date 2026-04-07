<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from '../components/ui/Button.vue'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import type { LoginRequest, PasswordRecoveryConfirmRequest, PasswordRecoveryRequest } from '../types'

const auth = useAuthStore()
const router = useRouter()

const step = ref<'credentials' | 'code'>('credentials')
const showPassword = ref(false)
const useRecoveryCode = ref(false)
const showRecovery = ref(false)

const form = ref<LoginRequest>({ username: '', password: '' })
const twoFaCode = ref('')
const recoveryCode = ref('')

const recoveryRequest = ref<PasswordRecoveryRequest>({ identifier: '' })
const recoveryConfirm = ref<PasswordRecoveryConfirmRequest>({ token: '', new_password: '' })
const recoveryLoading = ref(false)
const recoveryMessage = ref<string | null>(null)
const recoveryError = ref<string | null>(null)

onMounted(() => {
  if (auth.isAuthenticated) {
    router.replace('/')
  }
})

async function submitLogin(): Promise<void> {
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

  if (success) {
    router.replace('/')
  }
}

async function resendCode(): Promise<void> {
  twoFaCode.value = ''
  recoveryCode.value = ''
  useRecoveryCode.value = false
  await auth.login({ username: form.value.username, password: form.value.password })
}

function backToCredentials(): void {
  step.value = 'credentials'
  auth.error = null
  twoFaCode.value = ''
  recoveryCode.value = ''
  useRecoveryCode.value = false
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
    recoveryMessage.value = data.recovery_token ? `Token temporal: ${data.recovery_token}` : data.detail
    recoveryConfirm.value.token = data.recovery_token ?? recoveryConfirm.value.token
  } catch (error: unknown) {
    const response = error as { response?: { data?: { detail?: string } } }
    recoveryError.value = response.response?.data?.detail ?? 'No se pudo solicitar la recuperación'
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
  } catch (error: unknown) {
    const response = error as { response?: { data?: { detail?: string } } }
    recoveryError.value = response.response?.data?.detail ?? 'No se pudo actualizar la contraseña'
  } finally {
    recoveryLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4">
    <div class="grid w-full max-w-6xl overflow-hidden rounded-[2rem] border border-white/60 bg-white/90 shadow-[0_30px_100px_rgba(15,23,42,0.20)] backdrop-blur-xl lg:grid-cols-[1.15fr_0.85fr] dark:border-slate-800 dark:bg-slate-950/80">
      <div class="relative hidden overflow-hidden bg-gradient-to-br from-slate-950 via-sky-900 to-cyan-800 px-8 py-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div class="absolute inset-0 opacity-35" style="background-image: radial-gradient(circle at 20% 20%, rgba(255,255,255,0.18), transparent 24%), radial-gradient(circle at 80% 20%, rgba(125,211,252,0.20), transparent 20%), radial-gradient(circle at 40% 80%, rgba(34,211,238,0.14), transparent 24%);"></div>
        <div class="relative space-y-6">
          <div class="inline-flex items-center gap-3 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-sm font-semibold tracking-wide">
            <span class="flex h-8 w-8 items-center justify-center rounded-full bg-white/15 text-lg">S</span>
            SOPHIE ERP
          </div>
          <div class="space-y-4 max-w-xl">
            <p class="text-sm uppercase tracking-[0.3em] text-sky-200/90">Panel Maestro + ERP</p>
            <h1 class="text-4xl font-black leading-tight">Operación, soporte y control en una sola interfaz.</h1>
            <p class="text-base text-sky-100/80">Accede al entorno con credenciales de demo, revisa empresas, tickets y auditoría, y navega con una base visual más limpia y consistente.</p>
          </div>
        </div>

        <div class="relative grid gap-3 rounded-3xl border border-white/15 bg-white/10 p-5 text-sm text-sky-50/90 backdrop-blur-sm">
          <p class="text-xs font-semibold uppercase tracking-[0.25em] text-sky-200/80">Credenciales de prueba</p>
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="rounded-2xl border border-white/10 bg-white/10 p-4">
              <p class="text-xs uppercase tracking-wide text-sky-200/80">Superadmin Root</p>
              <p class="mt-2 font-semibold">root</p>
              <p class="font-mono text-sm text-sky-100">RootPass123!</p>
            </div>
            <div class="rounded-2xl border border-white/10 bg-white/10 p-4">
              <p class="text-xs uppercase tracking-wide text-sky-200/80">Superadmin Damacoria</p>
              <p class="mt-2 font-semibold">damacoria</p>
              <p class="font-mono text-sm text-sky-100">Docedos13</p>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white/80 px-6 py-8 sm:px-8 lg:px-10 dark:bg-slate-950/80">
        <div class="mb-6 flex items-center justify-between lg:hidden">
          <div>
            <p class="text-xs uppercase tracking-[0.3em] text-sky-600">SOPHIE ERP</p>
            <h1 class="text-2xl font-black text-slate-900 dark:text-slate-100">Acceso seguro</h1>
          </div>
          <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-600 to-cyan-600 text-xl font-bold text-white shadow-lg shadow-sky-600/25">S</div>
        </div>

        <div class="mb-4 hidden lg:block">
          <p class="text-xs uppercase tracking-[0.3em] text-sky-600">SOPHIE ERP</p>
          <h2 class="mt-2 text-2xl font-bold text-slate-900 dark:text-slate-100">Iniciar sesión</h2>
          <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">Usa las credenciales demo para validar el sistema completo.</p>
        </div>

        <div class="mb-6 flex items-center gap-2 px-1 pt-1">
          <div class="flex items-center gap-1.5 text-xs font-medium" :class="step === 'credentials' ? 'text-sky-700' : 'text-slate-400'">
            <span class="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold" :class="step === 'credentials' ? 'bg-sky-600 text-white' : 'bg-slate-200 text-slate-500'">1</span>
            Credenciales
          </div>
          <div class="h-px flex-1" :class="step === 'code' ? 'bg-sky-500' : 'bg-slate-200'"></div>
          <div class="flex items-center gap-1.5 text-xs font-medium" :class="step === 'code' ? 'text-sky-700' : 'text-slate-400'">
            <span class="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold" :class="step === 'code' ? 'bg-sky-600 text-white' : 'bg-slate-200 text-slate-500'">2</span>
            Verificación
          </div>
        </div>

        <form class="space-y-4" @submit.prevent="submitLogin">
          <template v-if="step === 'credentials'">
            <div>
              <label class="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">Usuario</label>
              <input
                v-model="form.username"
                type="text"
                required
                autocomplete="username"
                class="w-full rounded-2xl border border-slate-200 bg-white/90 px-4 py-3 text-sm outline-none transition focus:border-transparent focus:bg-white focus:ring-2 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-900/80 dark:focus:bg-slate-900"
                placeholder="nombre de usuario"
              />
            </div>
            <div>
              <label class="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">Contraseña</label>
              <div class="relative">
                <input
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  autocomplete="current-password"
                  class="w-full rounded-2xl border border-slate-200 bg-white/90 py-3 pl-4 pr-10 text-sm outline-none transition focus:border-transparent focus:bg-white focus:ring-2 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-900/80 dark:focus:bg-slate-900"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  tabindex="-1"
                  @click="showPassword = !showPassword"
                >
                  <svg v-if="!showPassword" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  <svg v-else class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                </button>
              </div>
            </div>
          </template>

          <template v-else>
            <div class="py-2 text-center">
              <div class="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-50 dark:bg-sky-950/40">
                <svg class="h-7 w-7 text-sky-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>

              <p v-if="!useRecoveryCode" class="text-sm font-medium text-slate-700 dark:text-slate-200">Código de verificación</p>
              <p v-else class="text-sm font-medium text-slate-700 dark:text-slate-200">Código de recuperación</p>

              <div v-if="!useRecoveryCode" class="mt-2 space-y-0.5">
                <p v-if="auth.mfaDestination" class="flex items-center justify-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                  <span>✉</span>
                  <span>{{ auth.mfaDestination }}</span>
                </p>
                <p v-if="auth.mfaPhoneDestination" class="flex items-center justify-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                  <span>📱</span>
                  <span>{{ auth.mfaPhoneDestination }}</span>
                </p>
              </div>

              <div v-if="auth.mfaDebugCode && !useRecoveryCode" class="mt-2 inline-flex items-center gap-1.5 rounded-xl border border-amber-200 bg-amber-50 px-3 py-1.5 dark:border-amber-800 dark:bg-amber-950/40">
                <svg class="h-3.5 w-3.5 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
                <span class="font-mono text-xs font-semibold text-amber-700 dark:text-amber-300">{{ auth.mfaDebugCode }}</span>
                <span class="text-xs text-amber-600 dark:text-amber-300">(dev)</span>
              </div>
            </div>

            <div v-if="!useRecoveryCode">
              <input
                v-model="twoFaCode"
                type="text"
                inputmode="numeric"
                pattern="[0-9]{6}"
                maxlength="6"
                autofocus
                class="w-full rounded-2xl border-2 border-slate-200 bg-white/90 px-4 py-4 text-center font-mono text-3xl tracking-[0.5em] outline-none transition focus:border-sky-500 focus:ring-0 dark:border-slate-700 dark:bg-slate-900/80 dark:focus:bg-slate-900"
                placeholder="------"
              />
              <p class="mt-1.5 text-center text-xs text-slate-400">Ingresa los 6 dígitos recibidos</p>
            </div>
            <div v-else>
              <input
                v-model="recoveryCode"
                type="text"
                autofocus
                class="w-full rounded-2xl border-2 border-slate-200 bg-white/90 px-4 py-3 text-center font-mono text-sm tracking-widest outline-none transition focus:border-sky-500 focus:ring-0 dark:border-slate-700 dark:bg-slate-900/80 dark:focus:bg-slate-900"
                placeholder="XXXX-XXXX-XXXX"
              />
              <p class="mt-1.5 text-center text-xs text-slate-400">Ingresa uno de tus códigos de recuperación guardados</p>
            </div>

            <div class="flex flex-col items-center gap-1 pt-1">
              <button
                v-if="auth.mfaChannel?.includes('email') || auth.mfaChannel?.includes('sms')"
                type="button"
                class="text-xs text-sky-600 hover:text-sky-800 hover:underline"
                @click="resendCode"
              >
                Reenviar código
              </button>
              <button
                type="button"
                class="text-xs text-slate-500 hover:text-sky-700 hover:underline"
                @click="useRecoveryCode = !useRecoveryCode"
              >
                {{ useRecoveryCode ? 'Usar código de verificación' : 'Usar código de recuperación' }}
              </button>
            </div>
          </template>

          <p v-if="auth.error" class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-800 dark:bg-red-950/35 dark:text-red-300">
            {{ auth.error }}
          </p>

          <div class="flex gap-3 pt-1">
            <button
              v-if="step === 'code'"
              type="button"
              class="inline-flex items-center justify-center rounded-2xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-900"
              @click="backToCredentials"
            >
              Volver
            </button>
            <Button type="submit" class="flex-1" :loading="auth.loading">{{ step === 'credentials' ? 'Continuar' : 'Entrar' }}</Button>
          </div>

          <button
            type="button"
            class="w-full text-center text-xs text-slate-500 hover:text-sky-700 hover:underline"
            @click="showRecovery = !showRecovery"
          >
            {{ showRecovery ? 'Ocultar recuperación' : '¿Olvidaste tu contraseña?' }}
          </button>

          <div v-if="showRecovery" class="mt-4 rounded-3xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/60">
            <p class="text-sm font-semibold text-slate-800 dark:text-slate-100">Recuperación de contraseña</p>
            <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">Si estás en desarrollo y usas las credenciales de demo, puedes solicitar un token temporal aquí mismo.</p>
            <div class="mt-4 space-y-3">
              <div>
                <label class="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-slate-500">Identificador</label>
                <input v-model="recoveryRequest.identifier" type="text" class="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-950" placeholder="usuario, email o teléfono" />
              </div>
              <div class="flex gap-2">
                <Button type="button" variant="secondary" class="flex-1" :loading="recoveryLoading" @click="requestRecoveryToken">Solicitar token</Button>
                <Button type="button" variant="ghost" class="flex-1" :loading="recoveryLoading" @click="confirmRecoveryPassword">Confirmar</Button>
              </div>
              <p v-if="recoveryMessage" class="rounded-2xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">{{ recoveryMessage }}</p>
              <p v-if="recoveryError" class="rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-800 dark:bg-red-950/35 dark:text-red-300">{{ recoveryError }}</p>
            </div>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>


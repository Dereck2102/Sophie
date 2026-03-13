<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from '../components/ui/Button.vue'
import { useAuthStore } from '../stores/auth'
import type { LoginRequest } from '../types'

const auth = useAuthStore()
const router = useRouter()

const form = ref<LoginRequest>({ username: '', password: '' })
const mfaCode = ref('')
const showMfa = ref(false)

onMounted(() => {
  if (auth.isAuthenticated) router.replace('/')
})

async function handleSubmit(): Promise<void> {
  const payload: LoginRequest = { ...form.value }
  if (showMfa.value) payload.mfa_code = mfaCode.value

  const success = await auth.login(payload)
  if (auth.mfaRequired && !showMfa.value) {
    showMfa.value = true
    return
  }
  if (success) router.replace('/')
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
            <p class="text-sm text-gray-600">Ingresa el código de tu aplicación autenticadora</p>
          </div>
          <input
            v-model="mfaCode"
            type="text"
            inputmode="numeric"
            pattern="[0-9]{6}"
            maxlength="6"
            autofocus
            class="w-full px-4 py-3 border border-gray-300 rounded-lg text-center text-2xl font-mono tracking-widest focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
            placeholder="000000"
          />
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
      </form>
    </div>
  </div>
</template>

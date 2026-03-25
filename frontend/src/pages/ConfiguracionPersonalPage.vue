<template>
  <div class="configuracion-personal-container">
    <div class="max-w-4xl mx-auto">
      <!-- Encabezado -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold mb-2">Mi Configuración Personal</h1>
        <p class="text-gray-600">Personaliza tu experiencia en SOPHIE ERP</p>
      </div>

      <!-- Alerta de tipo suscripción -->
      <div v-if="user?.tipo_suscripcion !== 'individual'" class="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p class="text-yellow-800">
          ⚠️ Esta página es solo para suscripciones individuales. Si eres parte de una empresa, accede a su configuración desde el panel de empresas.
        </p>
      </div>

      <!-- Contenido en tabs -->
      <div class="bg-white rounded-lg shadow">
        <!-- Tabs -->
        <div class="border-b flex gap-4 px-6">
          <button
            @click="activeTab = 'general'"
            :class="['tab-button', activeTab === 'general' && 'active']"
            class="py-4 px-4 border-b-2 border-transparent font-medium transition"
          >
            ⚙️ General
          </button>
          <button
            @click="activeTab = 'preferencias'"
            :class="['tab-button', activeTab === 'preferencias' && 'active']"
            class="py-4 px-4 border-b-2 border-transparent font-medium transition"
          >
            🎨 Preferencias
          </button>
          <button
            @click="activeTab = 'notificaciones'"
            :class="['tab-button', activeTab === 'notificaciones' && 'active']"
            class="py-4 px-4 border-b-2 border-transparent font-medium transition"
          >
            🔔 Notificaciones
          </button>
        </div>

        <!-- Tab Content -->
        <div class="p-6">
          <!-- Tab: General -->
          <div v-if="activeTab === 'general'" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FormGroup label="Nombre Completo">
                <div class="px-4 py-2 bg-gray-100 rounded-lg text-gray-700">{{user?.nombre_completo}}</div>
              </FormGroup>

              <FormGroup label="Email">
                <div class="px-4 py-2 bg-gray-100 rounded-lg text-gray-700">{{user?.email}}</div>
              </FormGroup>

              <FormGroup label="Timezone">
                <select
                  v-model="formData.timezone_personal"
                  class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="UTC">UTC</option>
                  <option value="America/Guayaquil">América/Ecuador (GMT-5)</option>
                  <option value="America/Lima">América/Perú (GMT-5)</option>
                  <option value="America/Bogota">América/Colombia (GMT-5)</option>
                  <option value="America/Mexico_City">América/México (GMT-6)</option>
                </select>
              </FormGroup>
            </div>

            <FormGroup label="Pie de Reporte (Personalizado)">
              <textarea
                v-model="formData.reporte_footer"
                rows="3"
                class="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Texto que aparecerá al pie de tus reportes"
              ></textarea>
            </FormGroup>
          </div>

          <!-- Tab: Preferencias -->
          <div v-if="activeTab === 'preferencias'" class="space-y-6">
            <FormGroup label="Idioma Preferido">
              <div class="flex gap-4">
                <label class="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    v-model="formData.preferencia_idioma"
                    value="es"
                    class="w-4 h-4"
                  />
                  <span>Español</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    v-model="formData.preferencia_idioma"
                    value="en"
                    class="w-4 h-4"
                  />
                  <span>English</span>
                </label>
              </div>
            </FormGroup>

            <FormGroup label="Tema">
              <div class="flex gap-4">
                <label class="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    v-model="formData.tema"
                    value="light"
                    class="w-4 h-4"
                  />
                  <span>☀️ Claro</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    v-model="formData.tema"
                    value="dark"
                    class="w-4 h-4"
                  />
                  <span>🌙 Oscuro</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    v-model="formData.tema"
                    value="system"
                    class="w-4 h-4"
                  />
                  <span>🖥️ Sistema</span>
                </label>
              </div>
            </FormGroup>

            <div class="bg-gray-50 p-4 rounded border border-gray-200">
              <p class="text-sm text-gray-600">
                💡 Nota: Las opciones de branding avanzado (logo, nombre, slogan) están disponibles únicamente para suscripciones corporativas (B2B).
              </p>
            </div>
          </div>

          <!-- Tab: Notificaciones -->
          <div v-if="activeTab === 'notificaciones'" class="space-y-6">
            <div class="flex items-center justify-between p-4 bg-gray-50 rounded border">
              <div>
                <h3 class="font-medium">📧 Notificaciones por Email</h3>
                <p class="text-sm text-gray-600">Recibe alertas importantes por correo</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  v-model="formData.notificaciones_email"
                  class="sr-only peer"
                />
                <div class="w-11 h-6 bg-gray-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            <div class="flex items-center justify-between p-4 bg-gray-50 rounded border">
              <div>
                <h3 class="font-medium">📱 Notificaciones por SMS</h3>
                <p class="text-sm text-gray-600">Recibe alertas críticas por mensaje de texto</p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  v-model="formData.notificaciones_sms"
                  class="sr-only peer"
                />
                <div class="w-11 h-6 bg-gray-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Botones de acción -->
      <div class="mt-6 flex gap-4 justify-end">
        <button
          @click="resetForm"
          class="px-6 py-2 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 transition"
        >
          ↺ Descartar Cambios
        </button>
        <button
          @click="saveForm"
          :disabled="isSaving"
          class="px-6 py-2 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition disabled:opacity-50"
        >
          {{ isSaving ? '⏳ Guardando...' : '💾 Guardar Cambios' }}
        </button>
      </div>

      <!-- Mensaje de éxito -->
      <div v-if="successMessage" class="mt-4 p-4 bg-green-50 border border-green-200 rounded text-green-800">
        ✅ {{successMessage}}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import type { ConfiguracionUsuario } from '../types'
import FormGroup from '../components/ui/FormGroup.vue'

const authStore = useAuthStore()
const activeTab = ref<'general' | 'preferencias' | 'notificaciones'>('general')
const isSaving = ref(false)
const successMessage = ref('')

const user = computed(() => authStore.user)

const formData = reactive<Partial<ConfiguracionUsuario>>({
  id_usuario: user.value?.id_usuario,
  timezone_personal: 'UTC',
  preferencia_idioma: 'es',
  tema: 'system',
  notificaciones_email: true,
  notificaciones_sms: false,
  reporte_footer: '',
})

const resetForm = () => {
  formData.timezone_personal = 'UTC'
  formData.preferencia_idioma = 'es'
  formData.tema = 'system'
  formData.notificaciones_email = true
  formData.notificaciones_sms = false
  formData.reporte_footer = ''
  successMessage.value = ''
}

const saveForm = async () => {
  isSaving.value = true
  successMessage.value = ''
  
  try {
    // TODO: Implementar endpoint POST /api/v1/usuario/configuracion
    // await configService.saveUserConfig(formData)
    
    successMessage.value = 'Configuración guardada exitosamente'
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  } catch (error) {
    console.error('Error saving config:', error)
    successMessage.value = 'Error al guardar la configuración'
  } finally {
    isSaving.value = false
  }
}

onMounted(() => {
  // TODO: Cargar configuración actual del usuario
  // const config = await configService.getUserConfig()
  // Object.assign(formData, config)
})
</script>

<style scoped>
.configuracion-personal-container {
  padding: 2rem 1rem;
  background-color: #f9fafb;
  min-height: 100vh;
}

.tab-button {
  color: #6b7280;
  border-color: transparent;
  transition: all 0.2s ease;
}

.tab-button:hover {
  color: #3b82f6;
}

.tab-button.active {
  color: #3b82f6;
  border-color: #3b82f6;
}
</style>

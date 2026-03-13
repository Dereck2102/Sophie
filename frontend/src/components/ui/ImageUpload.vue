<template>
  <div class="image-upload-wrapper">
    <input
      ref="inputRef"
      type="file"
      class="hidden"
      :accept="accept"
      :disabled="disabled"
      @change="onFileChange"
    />

    <!-- Preview -->
    <div v-if="currentImage" class="relative group mb-3">
      <img
        :src="currentImage"
        :alt="label"
        class="rounded-lg object-cover border border-gray-200"
        :class="previewClass"
      />
      <button
        v-if="!disabled"
        type="button"
        class="absolute top-1 right-1 bg-red-500 hover:bg-red-600 text-white rounded-full p-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity"
        @click="clearImage"
      >
        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
      <div v-if="imageInfo" class="text-xs text-gray-400 mt-1">
        {{ imageInfo.dimensions?.width }}×{{ imageInfo.dimensions?.height }}px ·
        {{ imageInfo.optimized_size_kb }} KB
        <span v-if="imageInfo.size_reduction_pct > 0" class="text-green-500">
          (ahorro -{{ imageInfo.size_reduction_pct }}%)
        </span>
      </div>
    </div>

    <!-- Dropzone -->
    <label
      v-if="!currentImage"
      :class="[
        'flex flex-col items-center justify-center border-2 border-dashed rounded-lg cursor-pointer transition-colors',
        isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50',
        disabled ? 'opacity-50 cursor-not-allowed' : '',
        dropzoneClass,
      ]"
      role="button"
      tabindex="0"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="openFilePicker"
      @keydown.enter.prevent="openFilePicker"
      @keydown.space.prevent="openFilePicker"
    >
      <div class="flex flex-col items-center py-4 px-3 text-center">
        <svg class="w-8 h-8 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <p class="text-sm text-gray-600">
          <span class="font-medium text-blue-600">Seleccionar imagen</span>
          o arrastrar aquí
        </p>
        <p class="text-xs text-gray-400 mt-1">{{ hintText }}</p>
      </div>
    </label>

    <!-- Change button if already has image -->
    <button
      v-if="currentImage && !disabled"
      type="button"
      class="mt-2 text-xs text-blue-600 hover:text-blue-800 transition-colors"
      @click="openFilePicker"
    >
      Cambiar imagen
    </button>

    <!-- Loading indicator -->
    <div v-if="loading" class="flex items-center gap-2 mt-2 text-sm text-gray-500">
      <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 22 6.477 22 12h-4z"></path>
      </svg>
      Optimizando imagen...
    </div>

    <!-- Error -->
    <p v-if="error" class="mt-1 text-xs text-red-500">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuthStore } from '../../stores/auth'
import api from '../../services/api'

const auth = useAuthStore()

interface ImageOptimizeResult {
  data_url: string
  original_size_kb: number
  optimized_size_kb: number
  size_reduction_pct: number
  format?: string
  dimensions?: { width: number; height: number }
}

interface Props {
  modelValue?: string | null
  label?: string
  imageType?: 'profile' | 'document' | 'gallery' | 'default'
  targetWidth?: number
  accept?: string
  disabled?: boolean
  previewClass?: string
  dropzoneClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  label: 'Imagen',
  imageType: 'default',
  accept: 'image/jpeg,image/png,image/webp',
  disabled: false,
  previewClass: 'w-full max-h-64',
  dropzoneClass: 'min-h-[120px]',
})

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
  'optimized': [result: ImageOptimizeResult]
  'error': [message: string]
}>()

const inputRef = ref<HTMLInputElement>()
const loading = ref(false)
const error = ref<string | null>(null)
const isDragging = ref(false)
const imageInfo = ref<ImageOptimizeResult | null>(null)

const currentImage = computed(() => props.modelValue)

const hintText = computed(() => {
  const limits: Record<string, string> = {
    profile: 'JPG, PNG o WebP · máx 500 KB',
    document: 'JPG, PNG o WebP · máx 2 MB',
    gallery: 'JPG, PNG o WebP · máx 1 MB',
    default: 'JPG, PNG o WebP · optimización automática',
  }
  return limits[props.imageType] ?? limits.default
})

function buildOptimizeEndpoints(): string[] {
  const configuredBase = String(api.defaults.baseURL ?? '')
  const usesVersionedBase = configuredBase.indexOf('/api/v1') !== -1
  if (usesVersionedBase) {
    return ['/images/optimize', '/api/v1/images/optimize']
  }
  return ['/api/v1/images/optimize', '/images/optimize']
}

async function processFile(file: File) {
  if (file.type.indexOf('image/') !== 0) {
    error.value = 'Solo se aceptan imágenes (JPG, PNG, WebP)'
    return
  }

  error.value = null
  loading.value = true

  try {
    const formData = new FormData()
    formData.append('file', file)
    if (props.imageType) formData.append('image_type', props.imageType)
    if (props.targetWidth) formData.append('target_width', String(props.targetWidth))

    const token = auth.accessToken ?? localStorage.getItem('access_token')
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined

    let result: ImageOptimizeResult | null = null
    let lastError: unknown = null
    for (const endpoint of buildOptimizeEndpoints()) {
      try {
        const response = await api.post<ImageOptimizeResult>(endpoint, formData, { headers })
        result = response.data
        break
      } catch (attemptError: unknown) {
        lastError = attemptError
        const err = attemptError as { response?: { status?: number } }
        if (err.response?.status !== 404) {
          throw attemptError
        }
      }
    }

    if (!result) {
      throw lastError ?? new Error('No se pudo resolver la ruta de optimización de imagen')
    }

    imageInfo.value = result
    emit('update:modelValue', result.data_url)
    emit('optimized', result)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    const msg = err.response?.data?.detail ?? (e instanceof Error ? e.message : 'Error procesando imagen')
    error.value = msg
    emit('error', msg)
  } finally {
    loading.value = false
  }
}

function openFilePicker() {
  if (props.disabled || loading.value) return
  inputRef.value?.click()
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) processFile(file)
  // Reset input para permitir re-selección del mismo archivo
  if (inputRef.value) inputRef.value.value = ''
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) processFile(file)
}

function clearImage() {
  imageInfo.value = null
  error.value = null
  emit('update:modelValue', null)
}
</script>

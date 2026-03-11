<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Wrench, CheckCircle, Clock, AlertCircle, Cpu, FileText } from 'lucide-vue-next'
import api from '../services/api'
import type { OrdenTrabajoPublic } from '../types'

const route = useRoute()
const token = route.params.token as string

const orden = ref<OrdenTrabajoPublic | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const estadoConfig: Record<string, { label: string; color: string; icon: typeof CheckCircle }> = {
  abierto: { label: 'Recibido', color: 'text-blue-600 bg-blue-50 border-blue-200', icon: FileText },
  en_progreso: { label: 'En reparación', color: 'text-amber-600 bg-amber-50 border-amber-200', icon: Wrench },
  esperando_cliente: { label: 'Esperando cliente', color: 'text-purple-600 bg-purple-50 border-purple-200', icon: AlertCircle },
  resuelto: { label: 'Reparado', color: 'text-emerald-600 bg-emerald-50 border-emerald-200', icon: CheckCircle },
  cerrado: { label: 'Entregado', color: 'text-gray-600 bg-gray-50 border-gray-200', icon: CheckCircle },
}

const estadoInfo = computed(() => estadoConfig[orden.value?.ticket_estado ?? ''] ?? { label: orden.value?.ticket_estado ?? '—', color: 'text-gray-600 bg-gray-50 border-gray-200', icon: FileText })

const progressSteps = [
  { key: 'abierto', label: 'Recibido' },
  { key: 'en_progreso', label: 'En reparación' },
  { key: 'resuelto', label: 'Reparado' },
  { key: 'cerrado', label: 'Entregado' },
]

const currentStepIndex = computed(() => {
  const estado = orden.value?.ticket_estado ?? ''
  const idx = progressSteps.findIndex((s) => s.key === estado)
  return idx >= 0 ? idx : 0
})

function formatDate(date?: string): string {
  if (!date) return '—'
  return new Date(date).toLocaleDateString('es-EC', {
    year: 'numeric', month: 'long', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatUSD(v?: number | null): string {
  if (v == null) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v)
}

onMounted(async () => {
  try {
    const { data } = await api.get<OrdenTrabajoPublic>(`/api/v1/tickets/seguimiento/${token}`)
    orden.value = data
  } catch {
    error.value = 'No se encontró la orden de trabajo. Verifica el enlace.'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 py-8 px-4">
    <div class="max-w-2xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4">
          <Wrench class="text-white" :size="32" />
        </div>
        <h1 class="text-2xl font-bold text-gray-900">SOPHIE</h1>
        <p class="text-gray-500 text-sm mt-1">Seguimiento de Orden de Trabajo</p>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center py-16">
        <svg class="animate-spin h-8 w-8 text-blue-600 mx-auto mb-3" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <p class="text-gray-500 text-sm">Cargando información...</p>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-2xl p-8 text-center">
        <AlertCircle class="text-red-400 mx-auto mb-3" :size="40" />
        <p class="text-red-700 font-medium">{{ error }}</p>
        <p class="text-red-500 text-sm mt-2">Si el problema persiste, contáctanos directamente.</p>
      </div>

      <!-- Content -->
      <div v-else-if="orden" class="space-y-4">

        <!-- Status Card -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          <div class="px-6 py-5 border-b border-gray-100">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-xs text-gray-400 font-medium uppercase tracking-wider">Ticket</p>
                <p class="text-xl font-bold text-gray-900 mt-0.5">{{ orden.ticket_numero }}</p>
                <p class="text-sm text-gray-600 mt-1">{{ orden.ticket_titulo }}</p>
              </div>
              <div :class="['flex items-center gap-2 px-3 py-2 rounded-xl border text-sm font-semibold', estadoInfo.color]">
                <component :is="estadoInfo.icon" :size="16" />
                {{ estadoInfo.label }}
              </div>
            </div>
          </div>

          <!-- Progress Steps -->
          <div class="px-6 py-5">
            <div class="flex items-center">
              <template v-for="(step, i) in progressSteps" :key="step.key">
                <div class="flex flex-col items-center">
                  <div :class="[
                    'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors',
                    i <= currentStepIndex ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
                  ]">
                    <CheckCircle v-if="i < currentStepIndex" :size="16" />
                    <span v-else>{{ i + 1 }}</span>
                  </div>
                  <span :class="['text-xs mt-1 text-center', i <= currentStepIndex ? 'text-blue-600 font-medium' : 'text-gray-400']">
                    {{ step.label }}
                  </span>
                </div>
                <div v-if="i < progressSteps.length - 1" :class="['flex-1 h-0.5 mx-1 mb-4', i < currentStepIndex ? 'bg-blue-600' : 'bg-gray-200']" />
              </template>
            </div>
          </div>
        </div>

        <!-- Equipment Details -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <h3 class="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <Cpu :size="18" class="text-blue-600" />
            Detalles del Equipo
          </h3>
          <div class="grid grid-cols-2 gap-3 text-sm">
            <div v-if="orden.equipo_descripcion" class="col-span-2">
              <span class="text-gray-500">Descripción:</span>
              <span class="ml-2 text-gray-800 font-medium">{{ orden.equipo_descripcion }}</span>
            </div>
            <div v-if="orden.marca_equipo">
              <span class="text-gray-500">Marca:</span>
              <span class="ml-2 text-gray-800 font-medium">{{ orden.marca_equipo }}</span>
            </div>
            <div v-if="orden.modelo_equipo">
              <span class="text-gray-500">Modelo:</span>
              <span class="ml-2 text-gray-800 font-medium">{{ orden.modelo_equipo }}</span>
            </div>
            <div v-if="orden.numero_serie_equipo" class="col-span-2">
              <span class="text-gray-500">N/S:</span>
              <span class="ml-2 text-gray-800 font-mono font-medium">{{ orden.numero_serie_equipo }}</span>
            </div>
            <div v-if="orden.accesorios_recibidos" class="col-span-2">
              <span class="text-gray-500">Accesorios recibidos:</span>
              <span class="ml-2 text-gray-800">{{ orden.accesorios_recibidos }}</span>
            </div>
          </div>
          <div v-if="!orden.equipo_descripcion && !orden.marca_equipo" class="text-gray-400 text-sm">
            Sin detalles de equipo registrados.
          </div>
        </div>

        <!-- Timeline -->
        <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <h3 class="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <Clock :size="18" class="text-blue-600" />
            Cronograma
          </h3>
          <div class="space-y-3 text-sm">
            <div class="flex justify-between py-2 border-b border-gray-50">
              <span class="text-gray-500">Ingreso del equipo</span>
              <span class="font-medium text-gray-800">{{ formatDate(orden.ticket_fecha_creacion) }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-gray-50">
              <span class="text-gray-500">Inicio de reparación</span>
              <span class="font-medium text-gray-800">{{ formatDate(orden.ticket_fecha_inicio) }}</span>
            </div>
            <div class="flex justify-between py-2">
              <span class="text-gray-500">Finalización</span>
              <span class="font-medium text-gray-800">{{ formatDate(orden.ticket_fecha_fin) }}</span>
            </div>
          </div>
        </div>

        <!-- Diagnosis & Cost -->
        <div v-if="orden.diagnostico || orden.costo_reparacion" class="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <h3 class="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <FileText :size="18" class="text-blue-600" />
            Diagnóstico y Costo
          </h3>
          <div class="space-y-3">
            <div v-if="orden.diagnostico">
              <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">Diagnóstico técnico</p>
              <p class="text-sm text-gray-800 bg-gray-50 rounded-lg p-3">{{ orden.diagnostico }}</p>
            </div>
            <div v-if="orden.repuestos.length > 0">
              <p class="text-xs text-gray-500 uppercase tracking-wider mb-2">Repuestos utilizados</p>
              <div class="space-y-1">
                <div v-for="r in orden.repuestos" :key="r.id_repuesto" class="flex justify-between text-sm py-1.5 border-b border-gray-50">
                  <span class="text-gray-700">Repuesto #{{ r.id_producto }} × {{ r.cantidad }}</span>
                  <span class="font-medium text-gray-800">{{ formatUSD(r.precio_unitario * r.cantidad) }}</span>
                </div>
              </div>
            </div>
            <div v-if="orden.costo_reparacion" class="flex justify-between items-center pt-3 border-t border-gray-100">
              <span class="font-semibold text-gray-700">Costo Total</span>
              <span class="text-lg font-bold text-blue-700">{{ formatUSD(orden.costo_reparacion) }}</span>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="text-center text-xs text-gray-400 py-4">
          <p>SOPHIE ERP/CRM — Big Solutions</p>
          <p class="mt-1">Para consultas adicionales, contacta con el taller directamente.</p>
        </div>
      </div>
    </div>
  </div>
</template>

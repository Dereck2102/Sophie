<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Building2, User, Mail, Phone, Clock } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Badge from '../components/ui/Badge.vue'
import { useClienteStore } from '../stores/clientes'
import type { Cliente, EventoCliente } from '../types'

const route = useRoute()
const router = useRouter()
const clienteStore = useClienteStore()

const cliente = ref<Cliente | null>(null)
const timeline = ref<EventoCliente[]>([])
const loading = ref(true)

const id = Number(route.params.id)

onMounted(async () => {
  const [clienteData, timelineData] = await Promise.all([
    clienteStore.fetchCliente(id),
    clienteStore.fetchTimeline(id),
  ])
  cliente.value = clienteData
  timeline.value = timelineData
  loading.value = false
})

const eventoIcon: Record<string, string> = {
  ALTA: '🆕',
  COTIZACION: '📄',
  FACTURA: '💰',
  TICKET: '🔧',
  BOVEDA: '🔒',
}

function formatDate(d: string): string {
  return new Date(d).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-4">
      <button @click="router.back()" class="p-2 hover:bg-gray-100 rounded-lg transition-colors">
        <ArrowLeft :size="20" />
      </button>
      <div>
        <h1 class="text-2xl font-bold text-gray-900">
          {{ cliente?.empresa?.razon_social ?? cliente?.cliente_b2c?.nombre_completo ?? 'Cliente' }}
        </h1>
        <p class="text-gray-500 text-sm">ID #{{ id }}</p>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-16">
      <svg class="animate-spin h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>

    <div v-else-if="cliente" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Info Column -->
      <div class="lg:col-span-2 space-y-4">
        <Card title="Información del Cliente">
          <div class="space-y-3">
            <div class="flex items-center gap-2">
              <Badge :variant="cliente.tipo_cliente === 'B2B' ? 'b2b' : 'b2c'">
                <component :is="cliente.tipo_cliente === 'B2B' ? Building2 : User" :size="11" class="mr-1" />
                {{ cliente.tipo_cliente }}
              </Badge>
              <Badge :variant="cliente.estado === 'activo' ? 'success' : cliente.estado === 'prospecto' ? 'warning' : 'default'">
                {{ cliente.estado }}
              </Badge>
            </div>

            <!-- B2B Info -->
            <template v-if="cliente.empresa">
              <div class="grid grid-cols-2 gap-4 mt-4">
                <div>
                  <p class="text-xs text-gray-400 uppercase font-medium">Razón Social</p>
                  <p class="text-sm font-semibold text-gray-800">{{ cliente.empresa.razon_social }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-400 uppercase font-medium">RUC</p>
                  <p class="text-sm font-semibold text-gray-800">{{ cliente.empresa.ruc }}</p>
                </div>
                <div v-if="cliente.empresa.contacto_principal">
                  <p class="text-xs text-gray-400 uppercase font-medium">Contacto</p>
                  <p class="text-sm text-gray-700 flex items-center gap-1"><User :size="13" /> {{ cliente.empresa.contacto_principal }}</p>
                </div>
                <div v-if="cliente.empresa.telefono">
                  <p class="text-xs text-gray-400 uppercase font-medium">Teléfono</p>
                  <p class="text-sm text-gray-700 flex items-center gap-1"><Phone :size="13" /> {{ cliente.empresa.telefono }}</p>
                </div>
                <div v-if="cliente.empresa.email">
                  <p class="text-xs text-gray-400 uppercase font-medium">Email</p>
                  <p class="text-sm text-gray-700 flex items-center gap-1"><Mail :size="13" /> {{ cliente.empresa.email }}</p>
                </div>
                <div v-if="cliente.empresa.sector">
                  <p class="text-xs text-gray-400 uppercase font-medium">Sector</p>
                  <p class="text-sm text-gray-700">{{ cliente.empresa.sector }}</p>
                </div>
              </div>
            </template>

            <!-- B2C Info -->
            <template v-else-if="cliente.cliente_b2c">
              <div class="grid grid-cols-2 gap-4 mt-4">
                <div>
                  <p class="text-xs text-gray-400 uppercase font-medium">Nombre Completo</p>
                  <p class="text-sm font-semibold text-gray-800">{{ cliente.cliente_b2c.nombre_completo }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-400 uppercase font-medium">Documento</p>
                  <p class="text-sm font-semibold text-gray-800">{{ cliente.cliente_b2c.documento_identidad }}</p>
                </div>
                <div v-if="cliente.cliente_b2c.telefono">
                  <p class="text-xs text-gray-400 uppercase font-medium">Teléfono</p>
                  <p class="text-sm text-gray-700 flex items-center gap-1"><Phone :size="13" /> {{ cliente.cliente_b2c.telefono }}</p>
                </div>
                <div v-if="cliente.cliente_b2c.email">
                  <p class="text-xs text-gray-400 uppercase font-medium">Email</p>
                  <p class="text-sm text-gray-700 flex items-center gap-1"><Mail :size="13" /> {{ cliente.cliente_b2c.email }}</p>
                </div>
              </div>
            </template>
          </div>
        </Card>
      </div>

      <!-- Timeline Column -->
      <div>
        <Card title="Historial de Actividad">
          <div v-if="timeline.length === 0" class="text-center py-6 text-gray-400 text-sm">
            Sin actividad registrada
          </div>
          <div v-else class="space-y-3">
            <div
              v-for="evento in timeline"
              :key="evento.id_evento"
              class="flex gap-3 text-sm"
            >
              <div class="text-lg leading-none mt-0.5">{{ eventoIcon[evento.tipo_evento] ?? '📌' }}</div>
              <div class="flex-1">
                <p class="text-gray-700">{{ evento.descripcion }}</p>
                <p class="text-xs text-gray-400 flex items-center gap-1 mt-0.5">
                  <Clock :size="11" />
                  {{ formatDate(evento.fecha) }}
                </p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>

    <div v-else class="text-center py-16 text-gray-400">Cliente no encontrado</div>
  </div>
</template>

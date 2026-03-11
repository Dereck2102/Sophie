<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Building2, User, Mail, Phone, Clock, Plus, Wrench, FileText } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import { useClienteStore } from '../stores/clientes'
import api from '../services/api'
import type { Cliente, EventoCliente, Ticket, Cotizacion } from '../types'

const route = useRoute()
const router = useRouter()
const clienteStore = useClienteStore()

const cliente = ref<Cliente | null>(null)
const timeline = ref<EventoCliente[]>([])
const tickets = ref<Ticket[]>([])
const cotizaciones = ref<Cotizacion[]>([])
const loading = ref(true)
const activeTab = ref<'info' | 'tickets' | 'cotizaciones'>('info')

const id = Number(route.params.id)

// Quick create ticket state
const showTicketModal = ref(false)
const ticketForm = ref({ titulo: '', descripcion: '', tipo: 'incidencia_it' as const, prioridad: 'media' as const })
const ticketSaving = ref(false)
const ticketError = ref<string | null>(null)

const clienteName = computed(() =>
  cliente.value?.empresa?.razon_social ?? cliente.value?.cliente_b2c?.nombre_completo ?? 'Cliente'
)

const priorityVariant: Record<string, 'danger' | 'warning' | 'info' | 'default'> = {
  critica: 'danger', alta: 'warning', media: 'info', baja: 'default',
}
const estadoTicketVariant: Record<string, 'warning' | 'info' | 'success' | 'default'> = {
  abierto: 'warning', en_progreso: 'info', resuelto: 'success', cerrado: 'default',
}
const estadoCotVariant: Record<string, 'default' | 'info' | 'success' | 'warning' | 'danger'> = {
  borrador: 'default', enviada: 'info', aprobada: 'success', rechazada: 'danger', facturada: 'success',
}

const eventoIcon: Record<string, string> = {
  ALTA: '🆕', COTIZACION: '📄', FACTURA: '💰', TICKET: '🔧', BOVEDA: '🔒',
}

function formatDate(d: string): string {
  return new Date(d).toLocaleDateString('es-PE', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

onMounted(async () => {
  const [clienteData, timelineData, ticketsData, cotizacionesData] = await Promise.all([
    clienteStore.fetchCliente(id),
    clienteStore.fetchTimeline(id),
    api.get<Ticket[]>(`/api/v1/clientes/${id}/tickets`).then((r) => r.data).catch(() => []),
    api.get<Cotizacion[]>(`/api/v1/clientes/${id}/cotizaciones`).then((r) => r.data).catch(() => []),
  ])
  cliente.value = clienteData
  timeline.value = timelineData
  tickets.value = ticketsData
  cotizaciones.value = cotizacionesData
  loading.value = false
})

async function handleCreateTicket(): Promise<void> {
  ticketSaving.value = true
  ticketError.value = null
  try {
    const { data } = await api.post<Ticket>('/api/v1/tickets/', {
      id_cliente: id,
      tipo: ticketForm.value.tipo,
      titulo: ticketForm.value.titulo,
      descripcion: ticketForm.value.descripcion || undefined,
      prioridad: ticketForm.value.prioridad,
    })
    tickets.value.unshift(data)
    timeline.value.unshift({
      id_evento: -Date.now(),
      tipo_evento: 'TICKET',
      descripcion: `Ticket ${data.numero} creado.`,
      fecha: new Date().toISOString(),
    })
    showTicketModal.value = false
    ticketForm.value = { titulo: '', descripcion: '', tipo: 'incidencia_it', prioridad: 'media' }
    activeTab.value = 'tickets'
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ticketError.value = err.response?.data?.detail ?? 'Error al crear ticket'
  } finally {
    ticketSaving.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header bar -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <button @click="router.back()" class="p-2 hover:bg-gray-100 rounded-lg transition-colors">
          <ArrowLeft :size="20" />
        </button>
        <div>
          <h1 class="text-2xl font-bold text-gray-900">{{ clienteName }}</h1>
          <p class="text-gray-500 text-sm">ID #{{ id }}</p>
        </div>
      </div>
      <div class="flex gap-2">
        <Button size="sm" variant="secondary" @click="showTicketModal = true">
          <Wrench :size="14" class="mr-1" />
          Nuevo Ticket
        </Button>
        <Button size="sm" @click="router.push('/ventas')">
          <FileText :size="14" class="mr-1" />
          Nueva Cotización
        </Button>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-16">
      <svg class="animate-spin h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>

    <div v-else-if="cliente" class="space-y-4">
      <!-- Tabs -->
      <div class="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        <button
          v-for="tab in [
            { id: 'info', label: 'Información' },
            { id: 'tickets', label: `Tickets (${tickets.length})` },
            { id: 'cotizaciones', label: `Cotizaciones (${cotizaciones.length})` },
          ]"
          :key="tab.id"
          @click="activeTab = tab.id as typeof activeTab"
          :class="[
            'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
            activeTab === tab.id
              ? 'bg-white text-gray-800 shadow-sm'
              : 'text-gray-500 hover:text-gray-700',
          ]"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- Tab: Información -->
      <div v-show="activeTab === 'info'" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
                  <div v-if="cliente.empresa.direccion" class="col-span-2">
                    <p class="text-xs text-gray-400 uppercase font-medium">Dirección</p>
                    <p class="text-sm text-gray-700">{{ cliente.empresa.direccion }}</p>
                  </div>
                </div>
              </template>

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
                  <div v-if="cliente.cliente_b2c.direccion" class="col-span-2">
                    <p class="text-xs text-gray-400 uppercase font-medium">Dirección</p>
                    <p class="text-sm text-gray-700">{{ cliente.cliente_b2c.direccion }}</p>
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
              <div v-for="evento in timeline" :key="evento.id_evento" class="flex gap-3 text-sm">
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

      <!-- Tab: Tickets -->
      <div v-show="activeTab === 'tickets'">
        <Card :padding="false">
          <div class="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <h3 class="font-semibold text-gray-800">Tickets de {{ clienteName }}</h3>
            <Button size="sm" @click="showTicketModal = true">
              <Plus :size="13" class="mr-1" /> Nuevo Ticket
            </Button>
          </div>
          <div v-if="tickets.length === 0" class="text-center py-10 text-gray-400 text-sm">
            No hay tickets para este cliente
          </div>
          <div v-else class="divide-y divide-gray-50">
            <div
              v-for="ticket in tickets"
              :key="ticket.id_ticket"
              class="flex items-center justify-between px-5 py-3 hover:bg-gray-50"
            >
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-800">{{ ticket.titulo }}</p>
                <p class="text-xs text-gray-400 mt-0.5">{{ ticket.numero }} · {{ ticket.tipo }} · {{ formatDate(ticket.fecha_creacion) }}</p>
              </div>
              <div class="flex gap-2 ml-3">
                <Badge :variant="priorityVariant[ticket.prioridad] ?? 'default'">{{ ticket.prioridad }}</Badge>
                <Badge :variant="estadoTicketVariant[ticket.estado] ?? 'default'">{{ ticket.estado.replace('_', ' ') }}</Badge>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <!-- Tab: Cotizaciones -->
      <div v-show="activeTab === 'cotizaciones'">
        <Card :padding="false">
          <div class="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <h3 class="font-semibold text-gray-800">Cotizaciones de {{ clienteName }}</h3>
            <Button size="sm" @click="router.push('/ventas')">
              <Plus :size="13" class="mr-1" /> Nueva Cotización
            </Button>
          </div>
          <div v-if="cotizaciones.length === 0" class="text-center py-10 text-gray-400 text-sm">
            No hay cotizaciones para este cliente
          </div>
          <div v-else class="divide-y divide-gray-50">
            <div
              v-for="cot in cotizaciones"
              :key="cot.id_cotizacion"
              class="flex items-center justify-between px-5 py-3 hover:bg-gray-50"
            >
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-800">{{ cot.numero }}</p>
                <p class="text-xs text-gray-400 mt-0.5">{{ formatDate(cot.fecha_creacion) }}</p>
              </div>
              <div class="flex items-center gap-3 ml-3">
                <span class="text-sm font-semibold text-gray-800">${{ Number(cot.total).toFixed(2) }}</span>
                <Badge :variant="estadoCotVariant[cot.estado] ?? 'default'">{{ cot.estado }}</Badge>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>

    <div v-else-if="!loading" class="text-center py-16 text-gray-400">Cliente no encontrado</div>

    <!-- Quick Ticket Modal -->
    <Modal :open="showTicketModal" title="Nuevo Ticket" size="md" @close="showTicketModal = false; ticketError = null">
      <form @submit.prevent="handleCreateTicket" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Título *</label>
          <input v-model="ticketForm.titulo" required type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
            <select v-model="ticketForm.tipo" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white">
              <option value="incidencia_it">Incidencia IT</option>
              <option value="reparacion">Reparación</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Prioridad</label>
            <select v-model="ticketForm.prioridad" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white">
              <option value="baja">Baja</option>
              <option value="media">Media</option>
              <option value="alta">Alta</option>
              <option value="critica">Crítica</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
          <textarea v-model="ticketForm.descripcion" rows="3" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none" />
        </div>
        <p v-if="ticketError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ ticketError }}</p>
        <div class="flex justify-end gap-3">
          <Button variant="secondary" type="button" @click="showTicketModal = false">Cancelar</Button>
          <Button type="submit" :loading="ticketSaving">Crear Ticket</Button>
        </div>
      </form>
    </Modal>
  </div>
</template>


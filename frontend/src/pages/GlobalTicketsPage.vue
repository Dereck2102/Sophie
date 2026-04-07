<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import api from '../services/api'
import type {
  EstadoTicket,
  GlobalTicket,
  GlobalTicketClientLookup,
  GlobalTicketProjectLookup,
  PrioridadTicket,
  TipoTicket,
  Usuario,
} from '../types'

const loading = ref(false)
const saving = ref(false)
const creating = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)

const tickets = ref<GlobalTicket[]>([])
const technicians = ref<Usuario[]>([])
const clients = ref<GlobalTicketClientLookup[]>([])
const clientProjects = ref<GlobalTicketProjectLookup[]>([])

const filters = ref<{
  estado: '' | EstadoTicket
  tipo: '' | TipoTicket
  id_empresa: '' | number
  id_tecnico: '' | number
}>({
  estado: '',
  tipo: '',
  id_empresa: '',
  id_tecnico: '',
})

const createForm = ref<{
  tipo: TipoTicket
  id_cliente: number | null
  id_proyecto: number | null
  id_tecnico: number | null
  prioridad: PrioridadTicket
  titulo: string
  descripcion: string
}>({
  tipo: 'incidencia_it',
  id_cliente: null,
  id_proyecto: null,
  id_tecnico: null,
  prioridad: 'media',
  titulo: '',
  descripcion: '',
})

const estadoOptions: Array<{ label: string; value: EstadoTicket }> = [
  { label: 'Abierto', value: 'abierto' },
  { label: 'En progreso', value: 'en_progreso' },
  { label: 'Esperando cliente', value: 'esperando_cliente' },
  { label: 'Resuelto', value: 'resuelto' },
  { label: 'Cerrado', value: 'cerrado' },
]

const tipoOptions: Array<{ label: string; value: TipoTicket }> = [
  { label: 'Incidencia IT', value: 'incidencia_it' },
  { label: 'Reparación', value: 'reparacion' },
]

const canCreate = computed(() => createForm.value.id_cliente && createForm.value.titulo.trim().length > 0)

const companyOptions = computed<Array<{ id: number; label: string }>>(() => {
  const map = new Map<number, string>()
  for (const client of clients.value) {
    if (client.id_empresa && client.empresa_nombre) {
      map.set(client.id_empresa, client.empresa_nombre)
    }
  }
  return Array.from(map.entries())
    .map(([id, label]) => ({ id, label }))
    .sort((a, b) => a.label.localeCompare(b.label, 'es'))
})

const clientOptions = computed<Array<{ id: number; label: string; companyId: number | null }>>(() => {
  const selectedCompanyId = Number(filters.value.id_empresa)
  const hasCompanyFilter = Number.isFinite(selectedCompanyId) && selectedCompanyId > 0
  const base = clients.value
    .map((client) => {
      const mainLabel = client.cliente_nombre?.trim() || `Cliente #${client.id_cliente}`
      const detail = client.tipo_cliente === 'B2B'
        ? `B2B · ${client.ruc ?? 'sin RUC'}`
        : 'B2C'
      return {
        id: client.id_cliente,
        label: `${mainLabel} (${detail})`,
        companyId: client.id_empresa ?? null,
      }
    })
    .sort((a, b) => a.label.localeCompare(b.label, 'es'))

  if (!hasCompanyFilter) return base
  return base.filter((item) => item.companyId === selectedCompanyId)
})

function parseApiError(e: unknown, fallback: string): string {
  const err = e as { response?: { data?: { detail?: string } } }
  return err.response?.data?.detail ?? fallback
}

async function loadTechnicians(): Promise<void> {
  try {
    const { data } = await api.get<Usuario[]>('/api/v1/usuarios/asignables')
    technicians.value = data
  } catch {
    technicians.value = []
  }
}

async function loadClients(): Promise<void> {
  try {
    const { data } = await api.get<GlobalTicketClientLookup[]>('/api/v1/global/tickets/lookups/clients', { params: { limit: 400 } })
    clients.value = data
  } catch {
    clients.value = []
  }
}

async function loadProjectsForClient(idCliente: number | null): Promise<void> {
  if (!idCliente) {
    clientProjects.value = []
    return
  }
  try {
    const { data } = await api.get<GlobalTicketProjectLookup[]>(`/api/v1/global/tickets/lookups/clients/${idCliente}/projects`, { params: { limit: 300 } })
    clientProjects.value = data
  } catch {
    clientProjects.value = []
  }
}

async function loadTickets(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const params: Record<string, string | number> = {}
    if (filters.value.estado) params.estado = filters.value.estado
    if (filters.value.tipo) params.tipo = filters.value.tipo
    if (filters.value.id_empresa) params.id_empresa = Number(filters.value.id_empresa)
    if (filters.value.id_tecnico) params.id_tecnico = Number(filters.value.id_tecnico)
    const { data } = await api.get<GlobalTicket[]>('/api/v1/global/tickets', { params })
    tickets.value = data
  } catch (e: unknown) {
    error.value = parseApiError(e, 'No se pudieron cargar los tickets globales')
  } finally {
    loading.value = false
  }
}

async function updateTicketEstado(ticket: GlobalTicket, estado: EstadoTicket): Promise<void> {
  saving.value = true
  error.value = null
  success.value = null
  try {
    await api.patch(`/api/v1/global/tickets/${ticket.id_ticket}`, { estado })
    success.value = `Estado actualizado para ${ticket.numero}`
    await loadTickets()
  } catch (e: unknown) {
    error.value = parseApiError(e, 'No se pudo actualizar el estado del ticket')
  } finally {
    saving.value = false
  }
}

async function updateTicketTecnico(ticket: GlobalTicket, id_tecnicoRaw: string): Promise<void> {
  const id_tecnico = Number(id_tecnicoRaw)
  if (!Number.isFinite(id_tecnico) || id_tecnico <= 0) return

  saving.value = true
  error.value = null
  success.value = null
  try {
    await api.patch(`/api/v1/global/tickets/${ticket.id_ticket}`, { id_tecnico })
    success.value = `Asignación actualizada para ${ticket.numero}`
    await loadTickets()
  } catch (e: unknown) {
    error.value = parseApiError(e, 'No se pudo actualizar la asignación del ticket')
  } finally {
    saving.value = false
  }
}

async function createTicket(): Promise<void> {
  if (!canCreate.value) return

  creating.value = true
  error.value = null
  success.value = null
  try {
    const tecnicoId = Number(createForm.value.id_tecnico)
    await api.post('/api/v1/global/tickets', {
      ...createForm.value,
      id_cliente: Number(createForm.value.id_cliente),
      id_proyecto: createForm.value.id_proyecto || null,
      id_tecnico: Number.isFinite(tecnicoId) && tecnicoId > 0 ? tecnicoId : null,
      descripcion: createForm.value.descripcion.trim() || null,
    })
    success.value = 'Ticket global creado correctamente'
    createForm.value = {
      tipo: 'incidencia_it',
      id_cliente: null,
      id_proyecto: null,
      id_tecnico: null,
      prioridad: 'media',
      titulo: '',
      descripcion: '',
    }
    await loadTickets()
  } catch (e: unknown) {
    error.value = parseApiError(e, 'No se pudo crear el ticket global')
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadTechnicians(), loadClients(), loadTickets()])
})

watch(
  () => filters.value.id_empresa,
  () => {
    const selected = createForm.value.id_cliente
    if (!selected) return
    const isStillVisible = clientOptions.value.some((item) => item.id === selected)
    if (!isStillVisible) {
      createForm.value.id_cliente = null
      createForm.value.id_proyecto = null
      clientProjects.value = []
    }
  }
)

watch(
  () => createForm.value.id_cliente,
  (value) => {
    createForm.value.id_proyecto = null
    void loadProjectsForClient(value)
  }
)
</script>

<template>
  <div class="space-y-6">
    <section class="rounded-2xl border border-gray-200 bg-white p-5">
      <h2 class="text-xl font-bold text-gray-900">Tickets Globales</h2>
      <p class="text-sm text-gray-600 mt-1">Mesa de soporte del Panel Maestro para superadmin y agente de soporte.</p>
    </section>

    <p v-if="error" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
    <p v-if="success" class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{{ success }}</p>

    <Card title="Filtros" subtitle="Listado global de tickets">
      <div class="grid grid-cols-1 gap-3 md:grid-cols-4">
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Estado</label>
          <select v-model="filters.estado" class="w-full rounded-lg border px-3 py-2 text-sm">
            <option value="">Todos</option>
            <option v-for="option in estadoOptions" :key="`filter-estado-${option.value}`" :value="option.value">{{ option.label }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Tipo</label>
          <select v-model="filters.tipo" class="w-full rounded-lg border px-3 py-2 text-sm">
            <option value="">Todos</option>
            <option v-for="option in tipoOptions" :key="`filter-tipo-${option.value}`" :value="option.value">{{ option.label }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Empresa</label>
          <select v-model="filters.id_empresa" class="w-full rounded-lg border px-3 py-2 text-sm">
            <option value="">Todas</option>
            <option v-for="company in companyOptions" :key="`filter-company-${company.id}`" :value="company.id">{{ company.label }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Técnico</label>
          <select v-model="filters.id_tecnico" class="w-full rounded-lg border px-3 py-2 text-sm">
            <option value="">Todos</option>
            <option v-for="tech in technicians" :key="`filter-tech-${tech.id_usuario}`" :value="tech.id_usuario">{{ tech.username }}</option>
          </select>
        </div>
        <div class="flex items-end md:col-span-4">
          <Button class="w-full" :loading="loading" @click="loadTickets">Aplicar filtros</Button>
        </div>
      </div>
    </Card>

    <Card title="Crear ticket global" subtitle="Registro rápido desde Panel Maestro">
      <form class="grid grid-cols-1 gap-3 md:grid-cols-3" @submit.prevent="createTicket">
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Cliente</label>
          <select v-model.number="createForm.id_cliente" class="w-full rounded-lg border px-3 py-2 text-sm" required>
            <option :value="null">Seleccionar cliente</option>
            <option v-for="client in clientOptions" :key="`create-client-${client.id}`" :value="client.id">{{ client.label }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Proyecto (opcional)</label>
          <select v-model.number="createForm.id_proyecto" class="w-full rounded-lg border px-3 py-2 text-sm" :disabled="!createForm.id_cliente">
            <option :value="null">Sin proyecto</option>
            <option v-for="project in clientProjects" :key="`create-project-${project.id_proyecto}`" :value="project.id_proyecto">
              #{{ project.id_proyecto }} · {{ project.nombre }}
            </option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Tipo</label>
          <select v-model="createForm.tipo" class="w-full rounded-lg border px-3 py-2 text-sm">
            <option v-for="option in tipoOptions" :key="`create-tipo-${option.value}`" :value="option.value">{{ option.label }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Prioridad</label>
          <select v-model="createForm.prioridad" class="w-full rounded-lg border px-3 py-2 text-sm">
            <option value="baja">Baja</option>
            <option value="media">Media</option>
            <option value="alta">Alta</option>
            <option value="critica">Crítica</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Asignar técnico</label>
          <select v-model="createForm.id_tecnico" class="w-full rounded-lg border px-3 py-2 text-sm">
            <option :value="null">Sin asignar</option>
            <option v-for="tech in technicians" :key="`create-tech-${tech.id_usuario}`" :value="tech.id_usuario">{{ tech.username }}</option>
          </select>
        </div>
        <div class="md:col-span-3">
          <label class="mb-1 block text-sm font-medium text-gray-700">Título</label>
          <input v-model="createForm.titulo" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" required />
        </div>
        <div class="md:col-span-3">
          <label class="mb-1 block text-sm font-medium text-gray-700">Descripción</label>
          <textarea v-model="createForm.descripcion" rows="2" class="w-full rounded-lg border px-3 py-2 text-sm" />
        </div>
        <div class="md:col-span-3 flex justify-end">
          <Button type="submit" :disabled="!canCreate" :loading="creating">Crear ticket</Button>
        </div>
      </form>
    </Card>

    <Card title="Tickets" subtitle="Estado y asignación">
      <div v-if="loading" class="text-sm text-gray-500">Cargando tickets...</div>
      <div v-else-if="tickets.length === 0" class="text-sm text-gray-500">No hay tickets para mostrar.</div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-gray-200 text-left">
              <th class="px-2 py-2">Ticket</th>
              <th class="px-2 py-2">Empresa/Cliente</th>
              <th class="px-2 py-2">Tipo</th>
              <th class="px-2 py-2">Estado</th>
              <th class="px-2 py-2">Asignado</th>
              <th class="px-2 py-2">Creado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ticket in tickets" :key="ticket.id_ticket" class="border-b border-gray-100 align-top">
              <td class="px-2 py-2">
                <p class="font-medium text-gray-900">{{ ticket.numero }}</p>
                <p class="text-xs text-gray-500">{{ ticket.titulo }}</p>
              </td>
              <td class="px-2 py-2">
                <p class="text-gray-900">{{ ticket.empresa_nombre ?? 'Sin empresa' }}</p>
                <p class="text-xs text-gray-500">{{ ticket.cliente_nombre ?? `Cliente #${ticket.id_cliente}` }}</p>
              </td>
              <td class="px-2 py-2 uppercase">{{ ticket.tipo }}</td>
              <td class="px-2 py-2">
                <select
                  class="w-full rounded-lg border px-2 py-1 text-xs"
                  :value="ticket.estado"
                  :disabled="saving"
                  @change="updateTicketEstado(ticket, ($event.target as HTMLSelectElement).value as EstadoTicket)"
                >
                  <option v-for="option in estadoOptions" :key="`estado-${ticket.id_ticket}-${option.value}`" :value="option.value">{{ option.label }}</option>
                </select>
              </td>
              <td class="px-2 py-2">
                <select
                  class="w-full rounded-lg border px-2 py-1 text-xs"
                  :value="ticket.id_tecnico ?? ''"
                  :disabled="saving"
                  @change="updateTicketTecnico(ticket, ($event.target as HTMLSelectElement).value)"
                >
                  <option value="" disabled>Seleccionar técnico</option>
                  <option v-for="tech in technicians" :key="`assign-${ticket.id_ticket}-${tech.id_usuario}`" :value="tech.id_usuario">{{ tech.username }}</option>
                </select>
              </td>
              <td class="px-2 py-2 text-gray-600">{{ new Date(ticket.fecha_creacion).toLocaleString('es-EC') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>
  </div>
</template>

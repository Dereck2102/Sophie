<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Plus, ScanLine, Camera, Trash2, AlertTriangle, Play, CheckSquare, Clock, X, ImageIcon, Printer, Link2, Copy, Check } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import { useClienteStore } from '../stores/clientes'
import { useTicketStore } from '../stores/tickets'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'
import type { Ticket, Reparacion, Cliente, Usuario, Proyecto } from '../types'

const ticketStore = useTicketStore()
const clienteStore = useClienteStore()
const auth = useAuthStore()
const route = useRoute()

const isTecnico = computed(() => auth.user?.rol === 'ejecutivo' || auth.user?.rol === 'tecnico')
const canCreate = computed(() => auth.user?.rol === 'superadmin' || auth.user?.rol === 'ejecutivo' || auth.user?.rol === 'tecnico')

const selectedTicket = ref<Ticket | null>(null)
const reparacion = ref<Reparacion | null>(null)
const showDetail = ref(false)
const showCreateModal = ref(false)
const showOrdenModal = ref(false)
const scannedCode = ref('')
const scanInput = ref<HTMLInputElement | null>(null)
const repuestos = ref<{ nombre: string; cantidad: number; precio: number }[]>([])
const fotoFiles = ref<File[]>([])
const fotoPreviews = ref<string[]>([])
const createFotoFiles = ref<File[]>([])
const createFotoPreviews = ref<string[]>([])
const nuevoRepuesto = ref({ nombre: '', cantidad: 1, precio: 0 })
const actionLoading = ref(false)
const actionError = ref<string | null>(null)
const saving = ref(false)
const formError = ref<string | null>(null)
const linkCopied = ref(false)
const reparacionLoading = ref(false)
const assignableUsers = ref<Usuario[]>([])
const proyectos = ref<Proyecto[]>([])

// New ticket form
function initialFormState() {
  return {
    tipo: 'reparacion',
    id_cliente: 0,
    id_proyecto: null as number | null,
    id_tecnico: null as number | null,
    prioridad: 'media',
    titulo: '',
    descripcion: '',
    equipo_descripcion: '',
    marca_equipo: '',
    modelo_equipo: '',
    numero_serie_equipo: '',
    accesorios_recibidos: '',
    email_cliente: '',
  }
}
const form = ref(initialFormState())

const selectedCreateCliente = computed<Cliente | undefined>(() =>
  clienteStore.clientes.find((cliente) => cliente.id_cliente === form.value.id_cliente)
)

const assignableOptions = computed(() =>
  assignableUsers.value.filter((usuario) => ['ejecutivo', 'tecnico', 'superadmin'].includes(usuario.rol))
)

const clientProjects = computed(() => {
  if (!form.value.id_cliente) return []
  return proyectos.value.filter((proyecto) => proyecto.id_cliente === form.value.id_cliente)
})

const clientTickets = computed(() => {
  if (!form.value.id_cliente) return []
  return ticketStore.tickets.filter((t) => t.id_cliente === form.value.id_cliente && t.tipo === 'reparacion')
})

const persistedFotos = computed(() => {
  if (!reparacion.value?.fotos_urls) return [] as string[]
  try {
    const parsed = JSON.parse(reparacion.value.fotos_urls)
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : []
  } catch {
    return []
  }
})

// Elapsed timer
const elapsedSeconds = ref(0)
let timerInterval: ReturnType<typeof setInterval> | null = null

const columns = [
  { key: 'numero', label: 'Ticket #' },
  { key: 'titulo', label: 'Descripción' },
  { key: 'prioridad', label: 'Prioridad', class: 'w-28' },
  { key: 'estado', label: 'Estado', class: 'w-36' },
  { key: 'tiempo', label: 'Tiempo', class: 'w-28' },
  { key: 'fecha_creacion', label: 'Fecha', class: 'w-36' },
  { key: 'acciones', label: 'Acciones', class: 'w-36' },
]

const priorityVariant: Record<string, 'danger' | 'warning' | 'info' | 'default'> = {
  critica: 'danger', alta: 'warning', media: 'info', baja: 'default',
}
const estadoVariant: Record<string, 'warning' | 'info' | 'success' | 'default'> = {
  abierto: 'warning', en_progreso: 'info', resuelto: 'success', cerrado: 'default',
}

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}h ${m}m ${s}s`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function ticketElapsed(ticket: Ticket): string {
  if (!ticket.fecha_inicio_trabajo) return '—'
  const start = new Date(ticket.fecha_inicio_trabajo).getTime()
  const end = ticket.fecha_fin_trabajo
    ? new Date(ticket.fecha_fin_trabajo).getTime()
    : Date.now()
  return formatDuration(Math.floor((end - start) / 1000))
}

const rows = computed(() =>
  ticketStore.tickets
    .filter((t) => t.tipo === 'reparacion')
    .map((t) => ({
      ...t,
      id: t.id_ticket,
      fecha_creacion: new Date(t.fecha_creacion).toLocaleDateString('es-EC'),
      tiempo: ticketElapsed(t),
    }))
)

const trackingUrl = computed(() => {
  if (!reparacion.value?.token_seguimiento) return null
  return `${window.location.origin}/orden/${reparacion.value.token_seguimiento}`
})

onMounted(async () => {
  await Promise.all([
    ticketStore.fetchTickets(),
    clienteStore.fetchClientes(),
    api.get<Proyecto[]>('/api/v1/proyectos/').then((response) => {
      proyectos.value = response.data
    }).catch(() => {
      proyectos.value = []
    }),
    api.get<Usuario[]>('/api/v1/usuarios/asignables').then((response) => {
      assignableUsers.value = response.data
    }).catch(() => {
      assignableUsers.value = []
    }),
  ])

  const clienteId = Number(route.query.clienteId)
  const proyectoId = Number(route.query.proyectoId)
  if (Number.isFinite(clienteId) && clienteId > 0) {
    form.value.id_cliente = clienteId
    if (typeof route.query.titulo === 'string') {
      form.value.titulo = route.query.titulo
    }
    if (typeof route.query.descripcion === 'string') {
      form.value.descripcion = route.query.descripcion
    }
    if (route.query.openCreate === '1') {
      showCreateModal.value = true
    }
  }
  if (Number.isFinite(proyectoId) && proyectoId > 0) {
    form.value.id_proyecto = proyectoId
  }
})

onUnmounted(() => {
  stopTimer()
})

function startTimer(ticket: Ticket): void {
  stopTimer()
  if (ticket.fecha_inicio_trabajo && !ticket.fecha_fin_trabajo) {
    const startMs = new Date(ticket.fecha_inicio_trabajo).getTime()
    elapsedSeconds.value = Math.floor((Date.now() - startMs) / 1000)
    timerInterval = setInterval(() => {
      elapsedSeconds.value++
    }, 1000)
  } else if (ticket.fecha_inicio_trabajo && ticket.fecha_fin_trabajo) {
    const startMs = new Date(ticket.fecha_inicio_trabajo).getTime()
    const endMs = new Date(ticket.fecha_fin_trabajo).getTime()
    elapsedSeconds.value = Math.floor((endMs - startMs) / 1000)
  } else {
    elapsedSeconds.value = 0
  }
}

function stopTimer(): void {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

async function openDetail(row: Record<string, unknown>): Promise<void> {
  const ticket = ticketStore.tickets.find((t) => t.id_ticket === row.id_ticket)
  if (ticket) {
    selectedTicket.value = ticket
    showDetail.value = true
    repuestos.value = []
    fotoFiles.value = []
    fotoPreviews.value = []
    scannedCode.value = ''
    reparacion.value = null
    startTimer(ticket)
    setTimeout(() => scanInput.value?.focus(), 100)

    // Load repair details
    if (ticket.tipo === 'reparacion') {
      reparacionLoading.value = true
      try {
        const { data } = await api.get<Reparacion>(`/api/v1/tickets/${ticket.id_ticket}/reparacion`)
        reparacion.value = data
      } catch {
        // not yet created or no permissions — ignore
      } finally {
        reparacionLoading.value = false
      }
    }
  }
}

async function openExistingTicket(ticket: Ticket): Promise<void> {
  showCreateModal.value = false
  selectedTicket.value = ticket
  showDetail.value = true
  repuestos.value = []
  fotoFiles.value = []
  fotoPreviews.value = []
  scannedCode.value = ''
  reparacion.value = null
  startTimer(ticket)
  setTimeout(() => scanInput.value?.focus(), 100)

  // Load repair details
  if (ticket.tipo === 'reparacion') {
    reparacionLoading.value = true
    try {
      const { data } = await api.get<Reparacion>(`/api/v1/tickets/${ticket.id_ticket}/reparacion`)
      reparacion.value = data
    } catch {
      // not yet created or no permissions — ignore
    } finally {
      reparacionLoading.value = false
    }
  }
}

function closeDetail(): void {
  showDetail.value = false
  stopTimer()
  elapsedSeconds.value = 0
  actionError.value = null
  fotoPreviews.value.forEach((url) => URL.revokeObjectURL(url))
  fotoFiles.value = []
  fotoPreviews.value = []
  reparacion.value = null
}

function extractTrackingToken(input: string): string | null {
  const normalized = input.trim()
  if (!normalized) return null

  try {
    const url = new URL(normalized)
    const parts = url.pathname.split('/').filter(Boolean)
    const ordenIndex = parts.findIndex((part) => part === 'orden')
    if (ordenIndex >= 0 && parts[ordenIndex + 1]) {
      return parts[ordenIndex + 1] || null
    }
  } catch {
    // Not a URL, continue with raw value
  }

  if (/^[A-Za-z0-9_-]{24,}$/.test(normalized)) {
    return normalized
  }

  return null
}

async function handleScan(): Promise<void> {
  const rawCode = scannedCode.value.trim()
  if (!rawCode) return

  actionError.value = null

  const byNumero = ticketStore.tickets.find(
    (ticket) => ticket.numero.toLowerCase() === rawCode.toLowerCase(),
  )
  if (byNumero) {
    scannedCode.value = ''
    await openExistingTicket(byNumero)
    scanInput.value?.focus()
    return
  }

  const token = extractTrackingToken(rawCode)
  if (token) {
    try {
      const { data } = await api.get<Ticket>(`/api/v1/tickets/seguimiento/${encodeURIComponent(token)}/ticket`)
      scannedCode.value = ''
      await openExistingTicket(data)
      scanInput.value?.focus()
      return
    } catch {
      actionError.value = 'No se encontró un ticket válido para el código escaneado'
    }
  } else {
    actionError.value = 'Código no reconocido. Escanea un número de ticket o enlace de seguimiento.'
  }

  scannedCode.value = ''
  scanInput.value?.focus()
}

function addRepuesto(): void {
  if (nuevoRepuesto.value.nombre) {
    repuestos.value.push({ ...nuevoRepuesto.value })
    nuevoRepuesto.value = { nombre: '', cantidad: 1, precio: 0 }
  }
}

function removeRepuesto(idx: number): void {
  repuestos.value.splice(idx, 1)
}

function handleFotoUpload(event: Event): void {
  const input = event.target as HTMLInputElement
  if (input.files) {
    Array.from(input.files).forEach((f) => {
      fotoFiles.value.push(f)
      const url = URL.createObjectURL(f)
      fotoPreviews.value.push(url)
    })
    input.value = ''
  }
}

function removeFoto(idx: number): void {
  const url = fotoPreviews.value[idx]
  if (url) URL.revokeObjectURL(url)
  fotoFiles.value.splice(idx, 1)
  fotoPreviews.value.splice(idx, 1)
}

function handleCreateFotoUpload(event: Event): void {
  const input = event.target as HTMLInputElement
  if (input.files) {
    Array.from(input.files).forEach((file) => {
      createFotoFiles.value.push(file)
      createFotoPreviews.value.push(URL.createObjectURL(file))
    })
    input.value = ''
  }
}

function removeCreateFoto(idx: number): void {
  const url = createFotoPreviews.value[idx]
  if (url) URL.revokeObjectURL(url)
  createFotoFiles.value.splice(idx, 1)
  createFotoPreviews.value.splice(idx, 1)
}

async function handleDeleteTicket(id: number): Promise<void> {
  if (!window.confirm('¿Eliminar este ticket? Esta acción no se puede deshacer.')) return
  try {
    await ticketStore.deleteTicket(id)
    if (selectedTicket.value?.id_ticket === id) {
      closeDetail()
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    actionError.value = err.response?.data?.detail ?? 'Error al eliminar el ticket'
  }
}

async function handleStart(): Promise<void> {
  if (!selectedTicket.value) return
  actionLoading.value = true
  actionError.value = null
  try {
    const updated = await ticketStore.startTicket(selectedTicket.value.id_ticket)
    selectedTicket.value = updated
    startTimer(updated)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    actionError.value = err.response?.data?.detail ?? 'Error al iniciar el ticket'
  } finally {
    actionLoading.value = false
  }
}

async function handleFinish(): Promise<void> {
  if (!selectedTicket.value) return
  actionLoading.value = true
  actionError.value = null
  try {
    const updated = await ticketStore.finishTicket(selectedTicket.value.id_ticket)
    selectedTicket.value = updated
    stopTimer()
    if (fotoFiles.value.length > 0) {
      reparacion.value = await ticketStore.uploadFotos(updated.id_ticket, fotoFiles.value)
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    actionError.value = err.response?.data?.detail ?? 'Error al finalizar el ticket'
  } finally {
    actionLoading.value = false
  }
}

async function handleCreate(): Promise<void> {
  if (!form.value.id_cliente || !form.value.titulo) {
    formError.value = 'Cliente y título son obligatorios'
    return
  }
  saving.value = true
  formError.value = null
  try {
    const payload = {
      tipo: form.value.tipo,
      id_cliente: Number(form.value.id_cliente),
      id_proyecto: form.value.id_proyecto || undefined,
      id_tecnico: form.value.id_tecnico || undefined,
      prioridad: form.value.prioridad,
      titulo: form.value.titulo,
      descripcion: form.value.descripcion || undefined,
      equipo_descripcion: form.value.equipo_descripcion || undefined,
      marca_equipo: form.value.marca_equipo || undefined,
      modelo_equipo: form.value.modelo_equipo || undefined,
      numero_serie_equipo: form.value.numero_serie_equipo || undefined,
      accesorios_recibidos: form.value.accesorios_recibidos || undefined,
      email_cliente: form.value.email_cliente || undefined,
    }
    const created = await ticketStore.createTicket(payload)
    if (createFotoFiles.value.length > 0) {
      await ticketStore.uploadFotos(created.id_ticket, createFotoFiles.value)
    }
    showCreateModal.value = false
    resetForm()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al crear ticket'
  } finally {
    saving.value = false
  }
}

function resetForm(): void {
  form.value = initialFormState()
  formError.value = null
  createFotoPreviews.value.forEach((url) => URL.revokeObjectURL(url))
  createFotoFiles.value = []
  createFotoPreviews.value = []
}

function printPage(): void {
  window.print()
}

async function copyTrackingLink(): Promise<void> {
  if (!trackingUrl.value) return
  try {
    await navigator.clipboard.writeText(trackingUrl.value)
    linkCopied.value = true
    setTimeout(() => { linkCopied.value = false }, 2000)
  } catch {
    alert(trackingUrl.value)
  }
}

const totalRepuestos = computed(() =>
  repuestos.value.reduce((s, r) => s + r.cantidad * r.precio, 0)
)

const ticketIsStarted = computed(() =>
  !!selectedTicket.value?.fecha_inicio_trabajo && !selectedTicket.value?.fecha_fin_trabajo
)
const ticketIsFinished = computed(() => !!selectedTicket.value?.fecha_fin_trabajo)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Taller de Reparaciones</h1>
        <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">
          {{ isTecnico ? 'Tus tickets asignados' : 'Gestión de tickets físicos de hardware' }}
        </p>
      </div>
      <Button v-if="canCreate" @click="showCreateModal = true">
        <Plus :size="16" class="mr-2" />
        Nuevo Ticket
      </Button>
    </div>

    <Card :padding="false">
      <Table :columns="columns" :rows="rows" :loading="ticketStore.loading" @row-click="openDetail">
        <template #prioridad="{ value }">
          <Badge :variant="priorityVariant[String(value)] ?? 'default'">{{ value }}</Badge>
        </template>
        <template #estado="{ value }">
          <Badge :variant="estadoVariant[String(value)] ?? 'default'">{{ value }}</Badge>
        </template>
        <template #tiempo="{ value }">
          <span class="flex items-center gap-1 text-xs text-gray-500">
            <Clock :size="12" />
            {{ value }}
          </span>
        </template>
        <template #acciones="{ row }">
          <button
            @click.stop="handleDeleteTicket(Number((row as Record<string, unknown>).id_ticket))"
            class="px-2 py-1 text-xs bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors inline-flex items-center gap-1"
            title="Eliminar ticket"
          >
            <Trash2 :size="13" /> Eliminar
          </button>
        </template>
      </Table>
    </Card>

    <!-- ─── Create Ticket Modal ──────────────────────────────────────────── -->
    <Modal :open="showCreateModal" title="Ingresar Equipo para Reparación" size="xl" @close="showCreateModal = false; resetForm()">
      <form @submit.prevent="handleCreate" class="space-y-5">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <!-- Client + Technician -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Cliente o empresa *</label>
            <select v-model.number="form.id_cliente" required class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100">
              <option :value="0">Selecciona un cliente</option>
              <option v-for="cliente in clienteStore.clientes" :key="cliente.id_cliente" :value="cliente.id_cliente">
                {{ cliente.empresa?.razon_social ?? cliente.cliente_b2c?.nombre_completo }}
              </option>
            </select>
            <p v-if="selectedCreateCliente" class="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {{ selectedCreateCliente.tipo_cliente }} · {{ selectedCreateCliente.estado }}
            </p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Técnico o encargado</label>
            <select v-model.number="form.id_tecnico" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100">
              <option :value="null">Sin asignar todavía</option>
              <option v-for="usuario in assignableOptions" :key="usuario.id_usuario" :value="usuario.id_usuario">
                {{ usuario.nombre_completo ?? usuario.username }} ({{ usuario.rol.replace('_', ' ') }})
              </option>
            </select>
          </div>

          <!-- Existing client tickets (NEW) -->
          <div v-if="form.id_cliente && clientTickets.length > 0" class="sm:col-span-2 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div class="flex items-center gap-2 mb-3">
              <CheckSquare :size="16" class="text-blue-600 dark:text-blue-400" />
              <h3 class="text-sm font-semibold text-blue-900 dark:text-blue-200">Tickets existentes del cliente</h3>
            </div>
            <div class="space-y-2">
              <button
                v-for="ticket in clientTickets"
                :key="ticket.id_ticket"
                type="button"
                @click="openExistingTicket(ticket)"
                class="w-full flex items-center justify-between p-3 bg-white dark:bg-gray-800 border border-blue-200 dark:border-blue-700 rounded-lg hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors text-left"
              >
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ ticket.titulo }}</p>
                  <p class="text-xs text-gray-500 dark:text-gray-400">{{ ticket.numero }} · {{ new Date(ticket.fecha_creacion).toLocaleDateString() }}</p>
                </div>
                <Badge :variant="ticket.estado === 'abierto' ? 'warning' : 'default'" class="text-xs">
                  {{ ticket.estado }}
                </Badge>
              </button>
            </div>
            <p class="text-xs text-blue-600 dark:text-blue-400 mt-2">Haz clic para abrir un ticket existente en lugar de crear uno nuevo</p>
          </div>

          <div class="sm:col-span-2">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Proyecto relacionado</label>
            <select v-model.number="form.id_proyecto" :disabled="!form.id_cliente" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white disabled:bg-gray-100 dark:bg-gray-700 dark:disabled:bg-gray-800 dark:text-gray-100">
              <option :value="null">Sin proyecto asociado</option>
              <option v-for="proyecto in clientProjects" :key="proyecto.id_proyecto" :value="proyecto.id_proyecto">
                {{ proyecto.nombre }}
              </option>
            </select>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">Solo aparecen proyectos del cliente seleccionado.</p>
          </div>

          <!-- Title + Priority -->
          <div class="sm:col-span-2">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Título del problema *</label>
            <input v-model="form.titulo" required type="text" placeholder="Ej: Laptop no enciende, pantalla rota..." class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Prioridad</label>
            <select v-model="form.prioridad" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100">
              <option value="baja">Baja</option>
              <option value="media">Media</option>
              <option value="alta">Alta</option>
              <option value="critica">Crítica</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email del Cliente</label>
            <input v-model="form.email_cliente" type="email" placeholder="Para enviar enlace de seguimiento" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
          </div>
        </div>

        <!-- Description -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Descripción del problema</label>
          <textarea v-model="form.descripcion" rows="2" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none dark:bg-gray-700 dark:text-gray-100" placeholder="Describe detalladamente el problema reportado por el cliente..." />
        </div>

        <div class="border border-gray-200 dark:border-gray-600 rounded-xl p-4 space-y-3">
          <div class="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
            <Camera :size="16" />
            Evidencia inicial del equipo
          </div>
          <label class="block w-full border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-4 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors">
            <input type="file" multiple accept="image/*" class="hidden" @change="handleCreateFotoUpload" />
            <div class="flex flex-col items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
              <ImageIcon :size="24" class="text-gray-400" />
              Adjuntar fotos del equipo al momento de ingreso
            </div>
          </label>
          <div v-if="createFotoPreviews.length > 0" class="grid grid-cols-3 gap-2">
            <div
              v-for="(preview, idx) in createFotoPreviews"
              :key="preview"
              class="relative rounded-lg overflow-hidden aspect-square bg-gray-100 dark:bg-gray-700"
            >
              <img :src="preview" :alt="`Foto inicial ${idx + 1}`" class="w-full h-full object-cover" />
              <button type="button" @click="removeCreateFoto(idx)" class="absolute top-1 right-1 bg-red-500 text-white rounded-full p-0.5">
                <X :size="12" />
              </button>
            </div>
          </div>
        </div>

        <!-- Equipment Details -->
        <div class="border border-gray-200 dark:border-gray-600 rounded-xl p-4 space-y-3">
          <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300">📦 Detalles del Equipo</h4>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Marca</label>
              <input v-model="form.marca_equipo" type="text" placeholder="Dell, HP, Apple..." class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Modelo</label>
              <input v-model="form.modelo_equipo" type="text" placeholder="Inspiron 15, MacBook Pro..." class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Número de Serie</label>
              <input v-model="form.numero_serie_equipo" type="text" placeholder="SN: ABC123..." class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
            </div>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Descripción del equipo</label>
            <input v-model="form.equipo_descripcion" type="text" placeholder="Laptop 15', negra, cargador incluido..." class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Accesorios recibidos</label>
            <input v-model="form.accesorios_recibidos" type="text" placeholder="Cargador, mouse, funda, cables..." class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
          </div>
        </div>

        <p v-if="formError" class="text-sm text-red-600 bg-red-50 dark:bg-red-900/30 px-3 py-2 rounded-lg">{{ formError }}</p>

        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" @click="showCreateModal = false; resetForm()">Cancelar</Button>
          <Button type="submit" :loading="saving">Registrar Equipo</Button>
        </div>
      </form>
    </Modal>

    <!-- ─── Taller Detail Modal ──────────────────────────────────────────── -->
    <Modal :open="showDetail" :title="`Ticket: ${selectedTicket?.numero}`" size="xl" @close="closeDetail">
      <div v-if="selectedTicket" class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- LEFT COLUMN: Timer + Scanner + Photos + Equipment info -->
        <div class="space-y-4">

          <!-- Equipment summary card (from reparacion) -->
          <div v-if="reparacion && (reparacion.marca_equipo || reparacion.equipo_descripcion)" class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-xl p-3 text-sm space-y-1">
            <p class="font-semibold text-blue-800 dark:text-blue-300 flex items-center gap-1.5">📦 Equipo Recibido</p>
            <p v-if="reparacion.marca_equipo || reparacion.modelo_equipo" class="text-blue-700 dark:text-blue-400">
              <span class="font-medium">{{ reparacion.marca_equipo }}</span>
              <span v-if="reparacion.modelo_equipo"> {{ reparacion.modelo_equipo }}</span>
            </p>
            <p v-if="reparacion.numero_serie_equipo" class="text-blue-600 dark:text-blue-400 font-mono text-xs">N/S: {{ reparacion.numero_serie_equipo }}</p>
            <p v-if="reparacion.accesorios_recibidos" class="text-blue-600 dark:text-blue-400 text-xs">Accesorios: {{ reparacion.accesorios_recibidos }}</p>
          </div>

          <!-- Timer & Action buttons -->
          <div class="rounded-xl border-2 p-4" :class="ticketIsFinished ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-700' : ticketIsStarted ? 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-700' : 'bg-gray-50 border-gray-200 dark:bg-gray-800 dark:border-gray-600'">
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-2">
                <Clock :size="18" :class="ticketIsFinished ? 'text-green-600' : ticketIsStarted ? 'text-blue-600' : 'text-gray-500'" />
                <span class="font-semibold text-sm" :class="ticketIsFinished ? 'text-green-700 dark:text-green-400' : ticketIsStarted ? 'text-blue-700 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'">
                  {{ ticketIsFinished ? 'Trabajo finalizado' : ticketIsStarted ? 'En progreso' : 'Sin iniciar' }}
                </span>
              </div>
              <span class="text-2xl font-mono font-bold" :class="ticketIsFinished ? 'text-green-700 dark:text-green-400' : ticketIsStarted ? 'text-blue-700 dark:text-blue-400' : 'text-gray-400'">
                {{ formatDuration(elapsedSeconds) }}
              </span>
            </div>

            <div class="flex gap-2">
              <Button
                v-if="!ticketIsStarted && !ticketIsFinished"
                class="flex-1"
                :loading="actionLoading"
                @click="handleStart"
              >
                <Play :size="14" class="mr-1" />
                Iniciar trabajo
              </Button>
              <Button
                v-if="ticketIsStarted"
                variant="success"
                class="flex-1"
                :loading="actionLoading"
                @click="handleFinish"
              >
                <CheckSquare :size="14" class="mr-1" />
                Finalizar trabajo
              </Button>
              <div v-if="ticketIsFinished" class="flex-1 text-center text-sm text-green-700 dark:text-green-400 font-medium py-2">
                ✓ Completado en {{ formatDuration(elapsedSeconds) }}
              </div>
            </div>
            <p v-if="actionError" class="text-xs text-red-600 bg-red-50 rounded-lg px-2 py-1 mt-2">{{ actionError }}</p>
          </div>

          <!-- Tracking link -->
          <div v-if="reparacion?.token_seguimiento" class="border border-emerald-200 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-3">
            <p class="text-xs font-semibold text-emerald-700 dark:text-emerald-400 mb-2 flex items-center gap-1.5">
              <Link2 :size="14" />
              Enlace de Seguimiento para Cliente
            </p>
            <div class="flex items-center gap-2">
              <input
                :value="trackingUrl"
                type="text"
                readonly
                class="flex-1 text-xs px-2 py-1.5 border border-emerald-300 dark:border-emerald-600 rounded-lg bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 truncate"
              />
              <button
                @click="copyTrackingLink"
                class="flex items-center gap-1 px-3 py-1.5 text-xs bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
              >
                <Check v-if="linkCopied" :size="13" />
                <Copy v-else :size="13" />
                {{ linkCopied ? 'Copiado' : 'Copiar' }}
              </button>
            </div>
          </div>

          <!-- Barcode/QR Scanner -->
          <div class="border-2 border-dashed border-blue-200 dark:border-blue-700 rounded-xl p-4 bg-blue-50 dark:bg-blue-900/20">
            <div class="flex items-center gap-2 mb-3 text-blue-700 dark:text-blue-400">
              <ScanLine :size="20" />
              <span class="font-semibold text-sm">Escáner de Código</span>
            </div>
            <input
              ref="scanInput"
              v-model="scannedCode"
              type="text"
              placeholder="Escanear código de barras o QR..."
              class="w-full px-3 py-2.5 border border-blue-300 dark:border-blue-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100"
              @keyup.enter="handleScan"
            />
            <p class="text-xs text-blue-500 mt-1">Apunta el escáner y presiona Enter</p>
          </div>

          <!-- Photo Upload -->
          <div>
            <div class="flex items-center gap-2 mb-2 text-gray-700 dark:text-gray-300">
              <Camera :size="18" />
              <span class="font-semibold text-sm">Fotos del Equipo</span>
              <span v-if="fotoFiles.length === 0 && persistedFotos.length === 0" class="text-xs text-amber-600 flex items-center gap-1">
                <AlertTriangle :size="12" />
                Aún sin evidencia cargada
              </span>
            </div>
            <label class="block w-full border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-4 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors">
              <input type="file" multiple accept="image/*" class="hidden" @change="handleFotoUpload" />
              <div class="flex flex-col items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
                <ImageIcon :size="24" class="text-gray-400" />
                Clic o arrastra imágenes aquí
              </div>
            </label>

            <!-- Image Previews -->
            <div v-if="fotoPreviews.length > 0" class="mt-3 grid grid-cols-3 gap-2">
              <div
                v-for="(preview, i) in fotoPreviews"
                :key="i"
                class="relative rounded-lg overflow-hidden group aspect-square bg-gray-100 dark:bg-gray-700"
              >
                <img :src="preview" class="w-full h-full object-cover" :alt="`Foto ${i + 1}`" />
                <button
                  @click="removeFoto(i)"
                  class="absolute top-1 right-1 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X :size="12" />
                </button>
              </div>
            </div>
            <div v-if="persistedFotos.length > 0" class="mt-3 grid grid-cols-3 gap-2">
              <a
                v-for="(foto, idx) in persistedFotos"
                :key="`${idx}-${foto.slice(0, 20)}`"
                :href="foto"
                target="_blank"
                rel="noreferrer"
                class="block rounded-lg overflow-hidden aspect-square bg-gray-100 dark:bg-gray-700"
              >
                <img :src="foto" :alt="`Foto registrada ${idx + 1}`" class="w-full h-full object-cover" />
              </a>
            </div>
          </div>

          <!-- Ticket Info -->
          <div class="text-sm space-y-1.5 text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
            <p><span class="font-medium text-gray-700 dark:text-gray-300">Descripción:</span> {{ selectedTicket.descripcion ?? '—' }}</p>
            <p><span class="font-medium text-gray-700 dark:text-gray-300">Prioridad:</span>
              <Badge class="ml-1 inline-flex" :variant="priorityVariant[selectedTicket.prioridad] ?? 'default'">{{ selectedTicket.prioridad }}</Badge>
            </p>
            <p><span class="font-medium text-gray-700 dark:text-gray-300">Estado:</span>
              <Badge class="ml-1 inline-flex" :variant="estadoVariant[selectedTicket.estado] ?? 'default'">{{ selectedTicket.estado }}</Badge>
            </p>
          </div>
        </div>

        <!-- RIGHT COLUMN: Repuestos + Actions -->
        <div class="space-y-4">
          <!-- Work Order Print Button -->
          <Button variant="secondary" class="w-full" @click="showOrdenModal = true">
            <Printer :size="14" class="mr-2" />
            Ver / Imprimir Orden de Trabajo
          </Button>

          <div class="font-semibold text-sm text-gray-700 dark:text-gray-300">Repuestos Utilizados</div>

          <!-- Add repuesto -->
          <div class="bg-gray-50 dark:bg-gray-800 rounded-xl p-3 space-y-2">
            <input
              v-model="nuevoRepuesto.nombre"
              type="text"
              placeholder="Nombre del repuesto"
              class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100"
            />
            <div class="flex gap-2">
              <input
                v-model.number="nuevoRepuesto.cantidad"
                type="number"
                min="1"
                placeholder="Cant."
                class="w-20 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100"
              />
              <input
                v-model.number="nuevoRepuesto.precio"
                type="number"
                min="0"
                step="0.01"
                placeholder="Precio $"
                class="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100"
              />
              <Button size="sm" @click="addRepuesto">+</Button>
            </div>
          </div>

          <!-- Repuesto list -->
          <div v-if="repuestos.length === 0" class="text-sm text-gray-400 text-center py-4">
            Sin repuestos añadidos
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="(r, i) in repuestos"
              :key="i"
              class="flex items-center justify-between bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm"
            >
              <div>
                <p class="font-medium text-gray-800 dark:text-gray-200">{{ r.nombre }}</p>
                <p class="text-xs text-gray-500">{{ r.cantidad }} × ${{ r.precio.toFixed(2) }}</p>
              </div>
              <div class="flex items-center gap-2">
                <span class="font-semibold text-gray-700 dark:text-gray-300">${{ (r.cantidad * r.precio).toFixed(2) }}</span>
                <button @click="removeRepuesto(i)" class="text-red-400 hover:text-red-600 transition-colors">
                  <Trash2 :size="15" />
                </button>
              </div>
            </div>
            <div class="flex justify-between font-semibold text-sm border-t border-gray-100 dark:border-gray-700 pt-2 text-gray-800 dark:text-gray-200">
              <span>Total Repuestos</span>
              <span>${{ totalRepuestos.toFixed(2) }}</span>
            </div>
          </div>

          <div class="flex gap-2 pt-2">
            <Button variant="secondary" class="flex-1" @click="closeDetail">Cerrar</Button>
          </div>
        </div>
      </div>
    </Modal>

    <!-- ─── Work Order Print Modal ──────────────────────────────────────── -->
    <Modal :open="showOrdenModal" title="Orden de Trabajo" size="lg" @close="showOrdenModal = false">
      <div v-if="selectedTicket" id="orden-trabajo-print" class="space-y-4">
        <div class="border-2 border-gray-300 rounded-xl p-5 space-y-4 print:border-black">
          <!-- Header -->
          <div class="flex justify-between items-start border-b border-gray-200 pb-4">
            <div>
              <h2 class="text-xl font-bold text-gray-900">ORDEN DE TRABAJO</h2>
              <p class="text-sm text-gray-500 mt-0.5">SOPHIE ERP/CRM — Big Solutions</p>
            </div>
            <div class="text-right">
              <p class="font-bold text-2xl text-blue-700">{{ selectedTicket.numero }}</p>
              <p class="text-xs text-gray-500">Fecha: {{ new Date(selectedTicket.fecha_creacion).toLocaleDateString('es-EC', { year: 'numeric', month: 'long', day: 'numeric' }) }}</p>
            </div>
          </div>

          <!-- Equipment -->
          <div class="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <div class="col-span-2 font-semibold text-gray-700 border-b border-gray-100 pb-1 mb-1">Información del Equipo</div>
            <div><span class="text-gray-500">Descripción:</span> <span class="font-medium">{{ reparacion?.equipo_descripcion || selectedTicket.titulo }}</span></div>
            <div><span class="text-gray-500">Marca:</span> <span class="font-medium">{{ reparacion?.marca_equipo || '—' }}</span></div>
            <div><span class="text-gray-500">Modelo:</span> <span class="font-medium">{{ reparacion?.modelo_equipo || '—' }}</span></div>
            <div><span class="text-gray-500">N/S:</span> <span class="font-mono font-medium">{{ reparacion?.numero_serie_equipo || '—' }}</span></div>
            <div class="col-span-2"><span class="text-gray-500">Accesorios:</span> <span class="font-medium">{{ reparacion?.accesorios_recibidos || 'Ninguno' }}</span></div>
          </div>

          <!-- Problem -->
          <div class="text-sm">
            <p class="font-semibold text-gray-700 border-b border-gray-100 pb-1 mb-2">Problema Reportado</p>
            <p class="text-gray-700 bg-gray-50 rounded-lg p-3">{{ selectedTicket.descripcion || selectedTicket.titulo }}</p>
          </div>

          <!-- Client Tracking -->
          <div v-if="trackingUrl" class="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm">
            <p class="font-semibold text-blue-700 mb-1">🔗 Seguimiento en Línea</p>
            <p class="text-blue-600 text-xs break-all">{{ trackingUrl }}</p>
            <p class="text-blue-500 text-xs mt-1">Escanea el código QR o visita este enlace para ver el progreso de tu reparación sin necesidad de iniciar sesión.</p>
          </div>

          <!-- Signature -->
          <div class="grid grid-cols-2 gap-6 pt-4 border-t border-gray-200 mt-4">
            <div class="text-center">
              <div class="border-b border-gray-400 h-12 mb-1"></div>
              <p class="text-xs text-gray-500">Firma del Cliente</p>
            </div>
            <div class="text-center">
              <div class="border-b border-gray-400 h-12 mb-1"></div>
              <p class="text-xs text-gray-500">Firma del Técnico</p>
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-3">
          <Button variant="secondary" @click="showOrdenModal = false">Cerrar</Button>
          <Button @click="printPage">
            <Printer :size="14" class="mr-2" />
            Imprimir
          </Button>
        </div>
      </div>
    </Modal>
  </div>
</template>

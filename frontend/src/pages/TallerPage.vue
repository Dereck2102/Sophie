<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { Plus, ScanLine, Camera, Trash2, AlertTriangle, Play, CheckSquare, Clock, X, ImageIcon } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import { useTicketStore } from '../stores/tickets'
import { useAuthStore } from '../stores/auth'
import type { Ticket } from '../types'

const ticketStore = useTicketStore()
const auth = useAuthStore()

const isTecnico = computed(() => auth.user?.rol === 'tecnico_taller' || auth.user?.rol === 'tecnico_it')

const selectedTicket = ref<Ticket | null>(null)
const showDetail = ref(false)
const scannedCode = ref('')
const scanInput = ref<HTMLInputElement | null>(null)
const repuestos = ref<{ nombre: string; cantidad: number; precio: number }[]>([])
const fotoFiles = ref<File[]>([])
const fotoPreviews = ref<string[]>([])
const nuevoRepuesto = ref({ nombre: '', cantidad: 1, precio: 0 })
const actionLoading = ref(false)
const actionError = ref<string | null>(null)

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
      fecha_creacion: new Date(t.fecha_creacion).toLocaleDateString('es-PE'),
      tiempo: ticketElapsed(t),
    }))
)

onMounted(() => {
  ticketStore.fetchTickets()
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

function openDetail(row: Record<string, unknown>): void {
  const ticket = ticketStore.tickets.find((t) => t.id_ticket === row.id_ticket)
  if (ticket) {
    selectedTicket.value = ticket
    showDetail.value = true
    repuestos.value = []
    fotoFiles.value = []
    fotoPreviews.value = []
    scannedCode.value = ''
    startTimer(ticket)
    setTimeout(() => scanInput.value?.focus(), 100)
  }
}

function closeDetail(): void {
  showDetail.value = false
  stopTimer()
  elapsedSeconds.value = 0
  actionError.value = null
  // Revoke all object URLs to prevent memory leaks
  fotoPreviews.value.forEach((url) => URL.revokeObjectURL(url))
  fotoFiles.value = []
  fotoPreviews.value = []
}

function handleScan(): void {
  if (scannedCode.value.trim()) {
    alert(`Código escaneado: ${scannedCode.value}`)
    scannedCode.value = ''
    scanInput.value?.focus()
  }
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
    // Upload photos if any
    if (fotoFiles.value.length > 0) {
      await ticketStore.uploadFotos(updated.id_ticket, fotoFiles.value)
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    actionError.value = err.response?.data?.detail ?? 'Error al finalizar el ticket'
  } finally {
    actionLoading.value = false
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
        <h1 class="text-2xl font-bold text-gray-900">Taller de Reparaciones</h1>
        <p class="text-gray-500 text-sm mt-1">
          {{ isTecnico ? 'Tus tickets asignados' : 'Gestión de tickets físicos de hardware' }}
        </p>
      </div>
      <Button v-if="!isTecnico">
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
      </Table>
    </Card>

    <!-- Taller Detail Modal - 2-column layout -->
    <Modal :open="showDetail" :title="`Ticket: ${selectedTicket?.numero}`" size="xl" @close="closeDetail">
      <div v-if="selectedTicket" class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- LEFT COLUMN: Timer + Scanner + Photos -->
        <div class="space-y-4">

          <!-- Timer & Action buttons -->
          <div class="rounded-xl border-2 p-4" :class="ticketIsFinished ? 'bg-green-50 border-green-200' : ticketIsStarted ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'">
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-2">
                <Clock :size="18" :class="ticketIsFinished ? 'text-green-600' : ticketIsStarted ? 'text-blue-600' : 'text-gray-500'" />
                <span class="font-semibold text-sm" :class="ticketIsFinished ? 'text-green-700' : ticketIsStarted ? 'text-blue-700' : 'text-gray-700'">
                  {{ ticketIsFinished ? 'Trabajo finalizado' : ticketIsStarted ? 'En progreso' : 'Sin iniciar' }}
                </span>
              </div>
              <span class="text-2xl font-mono font-bold" :class="ticketIsFinished ? 'text-green-700' : ticketIsStarted ? 'text-blue-700' : 'text-gray-400'">
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
              <div v-if="ticketIsFinished" class="flex-1 text-center text-sm text-green-700 font-medium py-2">
                ✓ Completado en {{ formatDuration(elapsedSeconds) }}
              </div>
            </div>
            <p v-if="actionError" class="text-xs text-red-600 bg-red-50 rounded-lg px-2 py-1 mt-2">{{ actionError }}</p>
          </div>

          <!-- Barcode/QR Scanner -->
          <div class="border-2 border-dashed border-blue-200 rounded-xl p-4 bg-blue-50">
            <div class="flex items-center gap-2 mb-3 text-blue-700">
              <ScanLine :size="20" />
              <span class="font-semibold text-sm">Escáner de Código</span>
            </div>
            <input
              ref="scanInput"
              v-model="scannedCode"
              type="text"
              placeholder="Escanear código de barras o QR..."
              class="w-full px-3 py-2.5 border border-blue-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none bg-white"
              @keyup.enter="handleScan"
            />
            <p class="text-xs text-blue-500 mt-1">Apunta el escáner y presiona Enter</p>
          </div>

          <!-- Photo Upload -->
          <div>
            <div class="flex items-center gap-2 mb-2 text-gray-700">
              <Camera :size="18" />
              <span class="font-semibold text-sm">Fotos del Equipo</span>
              <span v-if="fotoFiles.length < 3" class="text-xs text-amber-600 flex items-center gap-1">
                <AlertTriangle :size="12" />
                Mín. 3 fotos
              </span>
            </div>
            <label class="block w-full border-2 border-dashed border-gray-300 rounded-xl p-4 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
              <input type="file" multiple accept="image/*" class="hidden" @change="handleFotoUpload" />
              <div class="flex flex-col items-center gap-1 text-sm text-gray-500">
                <ImageIcon :size="24" class="text-gray-400" />
                Clic o arrastra imágenes aquí
              </div>
            </label>

            <!-- Image Previews -->
            <div v-if="fotoPreviews.length > 0" class="mt-3 grid grid-cols-3 gap-2">
              <div
                v-for="(preview, i) in fotoPreviews"
                :key="i"
                class="relative rounded-lg overflow-hidden group aspect-square bg-gray-100"
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
          </div>

          <!-- Ticket Info -->
          <div class="text-sm space-y-1.5 text-gray-600 bg-gray-50 rounded-lg p-3">
            <p><span class="font-medium text-gray-700">Descripción:</span> {{ selectedTicket.descripcion ?? '—' }}</p>
            <p><span class="font-medium text-gray-700">Prioridad:</span>
              <Badge class="ml-1 inline-flex" :variant="priorityVariant[selectedTicket.prioridad] ?? 'default'">{{ selectedTicket.prioridad }}</Badge>
            </p>
            <p><span class="font-medium text-gray-700">Estado:</span>
              <Badge class="ml-1 inline-flex" :variant="estadoVariant[selectedTicket.estado] ?? 'default'">{{ selectedTicket.estado }}</Badge>
            </p>
          </div>
        </div>

        <!-- RIGHT COLUMN: Repuestos -->
        <div class="space-y-4">
          <div class="font-semibold text-sm text-gray-700">Repuestos Utilizados</div>

          <!-- Add repuesto -->
          <div class="bg-gray-50 rounded-xl p-3 space-y-2">
            <input
              v-model="nuevoRepuesto.nombre"
              type="text"
              placeholder="Nombre del repuesto"
              class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            />
            <div class="flex gap-2">
              <input
                v-model.number="nuevoRepuesto.cantidad"
                type="number"
                min="1"
                placeholder="Cant."
                class="w-20 px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              />
              <input
                v-model.number="nuevoRepuesto.precio"
                type="number"
                min="0"
                step="0.01"
                placeholder="Precio S/"
                class="flex-1 px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
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
              class="flex items-center justify-between bg-white border rounded-lg px-3 py-2 text-sm"
            >
              <div>
                <p class="font-medium text-gray-800">{{ r.nombre }}</p>
                <p class="text-xs text-gray-500">{{ r.cantidad }} × S/ {{ r.precio.toFixed(2) }}</p>
              </div>
              <div class="flex items-center gap-2">
                <span class="font-semibold text-gray-700">S/ {{ (r.cantidad * r.precio).toFixed(2) }}</span>
                <button @click="removeRepuesto(i)" class="text-red-400 hover:text-red-600 transition-colors">
                  <Trash2 :size="15" />
                </button>
              </div>
            </div>
            <div class="flex justify-between font-semibold text-sm border-t pt-2 text-gray-800">
              <span>Total Repuestos</span>
              <span>S/ {{ totalRepuestos.toFixed(2) }}</span>
            </div>
          </div>

          <div class="flex gap-2 pt-2">
            <Button variant="secondary" class="flex-1" @click="closeDetail">Cerrar</Button>
          </div>
        </div>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Plus, ScanLine, Camera, Trash2, AlertTriangle } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import { useTicketStore } from '../stores/tickets'
import type { Ticket } from '../types'

const ticketStore = useTicketStore()

const selectedTicket = ref<Ticket | null>(null)
const showDetail = ref(false)
const scannedCode = ref('')
const scanInput = ref<HTMLInputElement | null>(null)
const repuestos = ref<{ nombre: string; cantidad: number; precio: number }[]>([])
const fotos = ref<string[]>([])
const nuevoRepuesto = ref({ nombre: '', cantidad: 1, precio: 0 })

const columns = [
  { key: 'numero', label: 'Ticket #' },
  { key: 'titulo', label: 'Descripción' },
  { key: 'prioridad', label: 'Prioridad', class: 'w-28' },
  { key: 'estado', label: 'Estado', class: 'w-32' },
  { key: 'fecha_creacion', label: 'Fecha', class: 'w-36' },
]

const priorityVariant: Record<string, 'danger' | 'warning' | 'info' | 'default'> = {
  critica: 'danger', alta: 'warning', media: 'info', baja: 'default',
}
const estadoVariant: Record<string, 'warning' | 'info' | 'success' | 'default'> = {
  abierto: 'warning', en_progreso: 'info', resuelto: 'success', cerrado: 'default',
}

const rows = computed(() =>
  ticketStore.tickets
    .filter((t) => t.tipo === 'reparacion')
    .map((t) => ({
      ...t,
      id: t.id_ticket,
      fecha_creacion: new Date(t.fecha_creacion).toLocaleDateString('es-PE'),
    }))
)

onMounted(() => {
  ticketStore.fetchTickets()
})

function openDetail(row: Record<string, unknown>): void {
  const ticket = ticketStore.tickets.find((t) => t.id_ticket === row.id_ticket)
  if (ticket) {
    selectedTicket.value = ticket
    showDetail.value = true
    repuestos.value = []
    fotos.value = []
    scannedCode.value = ''
    setTimeout(() => scanInput.value?.focus(), 100)
  }
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
    Array.from(input.files).forEach((f) => fotos.value.push(f.name))
  }
}

const totalRepuestos = computed(() =>
  repuestos.value.reduce((s, r) => s + r.cantidad * r.precio, 0)
)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Taller de Reparaciones</h1>
        <p class="text-gray-500 text-sm mt-1">Gestión de tickets físicos de hardware</p>
      </div>
      <Button>
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
      </Table>
    </Card>

    <!-- Taller Detail Modal - 2-column layout -->
    <Modal :open="showDetail" :title="`Ticket: ${selectedTicket?.numero}`" size="xl" @close="showDetail = false">
      <div v-if="selectedTicket" class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- LEFT COLUMN: Scanner + Photos -->
        <div class="space-y-4">
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
              autofocus
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
              <span v-if="fotos.length < 3" class="text-xs text-amber-600 flex items-center gap-1">
                <AlertTriangle :size="12" />
                Mín. 3 fotos requeridas
              </span>
            </div>
            <label class="block w-full border-2 border-dashed border-gray-300 rounded-xl p-4 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
              <input type="file" multiple accept="image/*" class="hidden" @change="handleFotoUpload" />
              <div class="text-sm text-gray-500">
                <Camera :size="24" class="mx-auto mb-1 text-gray-400" />
                Clic o arrastra fotos aquí
              </div>
            </label>
            <div v-if="fotos.length > 0" class="mt-2 flex flex-wrap gap-2">
              <span v-for="(foto, i) in fotos" :key="i" class="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">
                📷 {{ foto }}
              </span>
            </div>
          </div>

          <!-- Ticket Info -->
          <div class="text-sm space-y-1 text-gray-600">
            <p><span class="font-medium">Descripción:</span> {{ selectedTicket.descripcion ?? '—' }}</p>
            <p><span class="font-medium">Prioridad:</span> {{ selectedTicket.prioridad }}</p>
            <p><span class="font-medium">Estado:</span> {{ selectedTicket.estado }}</p>
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
            <Button variant="secondary" class="flex-1" @click="showDetail = false">Cerrar</Button>
            <Button class="flex-1">Guardar Cambios</Button>
          </div>
        </div>
      </div>
    </Modal>
  </div>
</template>

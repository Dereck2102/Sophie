<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, FolderOpen, ChevronRight, CheckSquare, Clock, Circle, ArrowLeft, User, Calendar, Flag, Tag, Trash2, Receipt } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import { useClienteStore } from '../stores/clientes'
import { useUsuarioStore } from '../stores/usuarios'
import type { CotizacionProyectoResumen, Proyecto, ProyectoRentabilidad, Tarea, EstadoProyecto, EstadoTarea } from '../types'

const proyectos = ref<Proyecto[]>([])
const tareas = ref<Tarea[]>([])
const loading = ref(true)
const selectedProject = ref<Proyecto | null>(null)
const projectMetrics = ref<ProyectoRentabilidad | null>(null)
const cotizacionesProyecto = ref<CotizacionProyectoResumen[]>([])
const selectedTarea = ref<Tarea | null>(null)
const tareasLoading = ref(false)
const cotizacionesLoading = ref(false)
const showCreateModal = ref(false)
const showTareaModal = ref(false)
const showTareaDetailModal = ref(false)
const saving = ref(false)
const formError = ref<string | null>(null)

const router = useRouter()
const auth = useAuthStore()
const clienteStore = useClienteStore()
const usuariosStore = useUsuarioStore()
const canDeleteProject = computed(() =>
  auth.user?.rol === 'superadmin' ||
  auth.user?.rol === 'ejecutivo'
)

function initialTareaFormState() {
  return {
    titulo: '',
    descripcion: '',
    estado: 'pendiente' as EstadoTarea,
    prioridad: 'media',
    id_asignado: null as number | null,
    fecha_vencimiento: '',
    etiquetas: '',
    horas_estimadas: '',
  }
}

const form = ref({
  id_cliente: 0,
  nombre: '',
  descripcion: '',
  estado: 'propuesta' as EstadoProyecto,
  presupuesto: '',
  fecha_inicio: '',
  fecha_fin: '',
})

const tareaForm = ref(initialTareaFormState())

const selectedCliente = computed(() =>
  clienteStore.clientes.find((cliente) => cliente.id_cliente === form.value.id_cliente)
)

const estadoVariant: Record<EstadoProyecto, 'default' | 'info' | 'success' | 'warning' | 'danger'> = {
  propuesta: 'info', en_progreso: 'warning', pausado: 'default', completado: 'success', cancelado: 'danger',
}
const estadoLabel: Record<EstadoProyecto, string> = {
  propuesta: 'Propuesta', en_progreso: 'En Progreso', pausado: 'Pausado', completado: 'Completado', cancelado: 'Cancelado',
}

const prioridadVariant: Record<string, 'danger' | 'warning' | 'info' | 'default'> = {
  critica: 'danger', alta: 'warning', media: 'info', baja: 'default',
}
const prioridadColor: Record<string, string> = {
  critica: 'text-red-500', alta: 'text-amber-500', media: 'text-blue-500', baja: 'text-gray-400',
}
const estadoCotizacionLabel: Record<string, string> = {
  borrador: 'Borrador',
  enviada: 'Enviada',
  aprobada: 'Aprobada',
  rechazada: 'Rechazada',
  facturada: 'Facturada',
}

const rows = computed(() =>
  proyectos.value.map((p) => ({
    ...p,
    id: p.id_proyecto,
    presupuesto: p.presupuesto ? `$${Number(p.presupuesto).toFixed(2)}` : '—',
    fecha_creacion: new Date(p.fecha_creacion).toLocaleDateString('en-US'),
  }))
)

const kanbanColumns: { estado: EstadoTarea; label: string; icon: typeof CheckSquare; color: string }[] = [
  { estado: 'pendiente', label: 'Pendiente', icon: Circle, color: 'text-gray-500' },
  { estado: 'en_progreso', label: 'En Progreso', icon: Clock, color: 'text-blue-500' },
  { estado: 'completado', label: 'Completado', icon: CheckSquare, color: 'text-emerald-500' },
]

const tareasByEstado = computed(() => {
  const grouped: Record<EstadoTarea, Tarea[]> = { pendiente: [], en_progreso: [], completado: [] }
  tareas.value.forEach((t) => {
    const key = t.estado as EstadoTarea
    if (grouped[key]) grouped[key].push(t)
  })
  return grouped
})

function getUserName(id?: number | null): string {
  if (!id) return '—'
  const u = usuariosStore.usuarios.find((u) => u.id_usuario === id)
  return u ? (u.nombre_completo ?? u.username) : `#${id}`
}

function getClientName(id: number): string {
  const cliente = clienteStore.clientes.find((item) => item.id_cliente === id)
  return cliente?.empresa?.razon_social ?? cliente?.cliente_b2c?.nombre_completo ?? `Cliente #${id}`
}

function formatUSD(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function isOverdue(tarea: Tarea): boolean {
  if (!tarea.fecha_vencimiento) return false
  return new Date(tarea.fecha_vencimiento) < new Date() && tarea.estado !== 'completado'
}

function parseEtiquetas(raw?: string): string[] {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) return parsed as string[]
  } catch (err) {
    if (import.meta.env.DEV) console.warn('parseEtiquetas: invalid JSON', raw, err)
  }
  return []
}

onMounted(async () => {
  try {
    const [proyRes] = await Promise.all([
      api.get<Proyecto[]>('/api/v1/proyectos/'),
      clienteStore.fetchClientes(),
      usuariosStore.fetchUsuarios(),
    ])
    proyectos.value = proyRes.data
  } finally {
    loading.value = false
  }
})

async function openProject(row: Record<string, unknown>): Promise<void> {
  const p = proyectos.value.find((x) => x.id_proyecto === row.id_proyecto)
  if (!p) return
  selectedProject.value = p
  tareasLoading.value = true
  cotizacionesLoading.value = true
  tareas.value = []
  projectMetrics.value = null
  cotizacionesProyecto.value = []
  try {
    const [tareasRes, metricsRes, cotizacionesRes] = await Promise.all([
      api.get<Tarea[]>(`/api/v1/proyectos/${p.id_proyecto}/tareas`),
      api.get<ProyectoRentabilidad>(`/api/v1/proyectos/${p.id_proyecto}/rentabilidad`),
      api.get<CotizacionProyectoResumen[]>(`/api/v1/proyectos/${p.id_proyecto}/cotizaciones`),
    ])
    tareas.value = tareasRes.data
    projectMetrics.value = metricsRes.data
    cotizacionesProyecto.value = cotizacionesRes.data
  } finally {
    tareasLoading.value = false
    cotizacionesLoading.value = false
  }
}

async function updateTareaEstado(id: number, estado: EstadoTarea): Promise<void> {
  try {
    const { data } = await api.patch<Tarea>(`/api/v1/proyectos/tareas/${id}`, { estado })
    const idx = tareas.value.findIndex((t) => t.id_tarea === id)
    if (idx >= 0) tareas.value[idx] = data
  } catch {
    // silently ignore
  }
}

async function deleteTarea(id: number): Promise<void> {
  if (!window.confirm('¿Estás seguro de que quieres eliminar esta tarea?')) {
    return
  }
  try {
    await api.delete(`/api/v1/proyectos/tareas/${id}`)
    tareas.value = tareas.value.filter((t) => t.id_tarea !== id)
    showTareaDetailModal.value = false
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    alert(err.response?.data?.detail ?? 'Error al eliminar tarea')
  }
}

async function handleCreate(): Promise<void> {
  saving.value = true
  formError.value = null
  try {
    const payload = {
      id_cliente: Number(form.value.id_cliente),
      nombre: form.value.nombre,
      descripcion: form.value.descripcion || undefined,
      estado: form.value.estado,
      presupuesto: form.value.presupuesto ? Number(form.value.presupuesto) : undefined,
      fecha_inicio: form.value.fecha_inicio || undefined,
      fecha_fin: form.value.fecha_fin || undefined,
    }
    const { data } = await api.post<Proyecto>('/api/v1/proyectos/', payload)
    proyectos.value.unshift(data)
    showCreateModal.value = false
    resetForm()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al crear proyecto'
  } finally {
    saving.value = false
  }
}

async function handleCreateTarea(): Promise<void> {
  if (!selectedProject.value) return
  saving.value = true
  formError.value = null
  try {
    // Convert comma-separated tags string to JSON array
    const etiquetasArray = tareaForm.value.etiquetas
      ? tareaForm.value.etiquetas.split(',').map((t) => t.trim()).filter(Boolean)
      : undefined
    const payload = {
      titulo: tareaForm.value.titulo,
      descripcion: tareaForm.value.descripcion || undefined,
      estado: tareaForm.value.estado,
      prioridad: tareaForm.value.prioridad,
      id_asignado: tareaForm.value.id_asignado || undefined,
      fecha_vencimiento: tareaForm.value.fecha_vencimiento || undefined,
      etiquetas: etiquetasArray ? JSON.stringify(etiquetasArray) : undefined,
      horas_estimadas: tareaForm.value.horas_estimadas ? Number(tareaForm.value.horas_estimadas) : undefined,
    }
    const { data } = await api.post<Tarea>(`/api/v1/proyectos/${selectedProject.value.id_proyecto}/tareas`, payload)
    tareas.value.push(data)
    showTareaModal.value = false
    resetTareaForm()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al crear tarea'
  } finally {
    saving.value = false
  }
}

function resetForm(): void {
  form.value = { id_cliente: 0, nombre: '', descripcion: '', estado: 'propuesta', presupuesto: '', fecha_inicio: '', fecha_fin: '' }
  formError.value = null
}

function resetTareaForm(): void {
  tareaForm.value = initialTareaFormState()
  formError.value = null
}

function openTareaDetail(tarea: Tarea): void {
  selectedTarea.value = tarea
  showTareaDetailModal.value = true
}

async function openTallerFromProyecto(): Promise<void> {
  if (!selectedProject.value) return
  await router.push({
    path: '/taller',
    query: {
      clienteId: String(selectedProject.value.id_cliente),
      proyectoId: String(selectedProject.value.id_proyecto),
      openCreate: '1',
      titulo: `Ingreso a taller · ${selectedProject.value.nombre}`,
      descripcion: `Solicitud vinculada al proyecto ${selectedProject.value.nombre}`,
    },
  })
}

async function openVentasFromProyecto(): Promise<void> {
  if (!selectedProject.value) return
  await router.push({
    path: '/ventas',
    query: {
      proyectoId: String(selectedProject.value.id_proyecto),
      clienteId: String(selectedProject.value.id_cliente),
      openCreate: '1',
    },
  })
}

async function handleDeleteProyecto(idProyecto: number): Promise<void> {
  if (!window.confirm('¿Eliminar este proyecto?')) return
  try {
    await api.delete(`/api/v1/proyectos/${idProyecto}`)
    proyectos.value = proyectos.value.filter((proyecto) => proyecto.id_proyecto !== idProyecto)
    if (selectedProject.value?.id_proyecto === idProyecto) {
      selectedProject.value = null
      tareas.value = []
      cotizacionesProyecto.value = []
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    alert(err.response?.data?.detail ?? 'Error al eliminar proyecto')
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div v-if="!selectedProject" class="p-2 bg-blue-600 rounded-xl">
          <FolderOpen class="text-white" :size="22" />
        </div>
        <button v-else @click="selectedProject = null; tareas = []" class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
          <ArrowLeft :size="20" class="text-gray-700 dark:text-gray-300" />
        </button>
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
            {{ selectedProject ? selectedProject.nombre : 'Proyectos & Asesoría' }}
          </h1>
          <p class="text-gray-500 dark:text-gray-400 text-sm mt-1">
            {{ selectedProject ? `${getClientName(selectedProject.id_cliente)} · ${estadoLabel[selectedProject.estado]}` : 'Gestión de proyectos de software y ciberseguridad' }}
          </p>
        </div>
      </div>
      <div class="flex gap-2">
        <Button v-if="selectedProject && canDeleteProject" size="sm" variant="danger" @click="handleDeleteProyecto(selectedProject.id_proyecto)">
          <Trash2 :size="14" class="mr-1" />
          Eliminar Proyecto
        </Button>
        <Button v-if="selectedProject" size="sm" variant="secondary" @click="openTallerFromProyecto">
          <Plus :size="14" class="mr-1" />
          Ticket de Taller
        </Button>
        <Button v-if="selectedProject" size="sm" variant="secondary" @click="showTareaModal = true">
          <Plus :size="14" class="mr-1" />
          Nueva Tarea
        </Button>
        <Button v-else @click="showCreateModal = true">
          <Plus :size="16" class="mr-2" />
          Nuevo Proyecto
        </Button>
      </div>
    </div>

    <!-- Project List -->
    <div v-if="!selectedProject">
      <Card :padding="false">
        <div v-if="loading" class="flex justify-center py-8">
          <svg class="animate-spin h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
        <div v-else-if="rows.length === 0" class="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
          No hay proyectos registrados
        </div>
        <div v-else class="divide-y divide-gray-50 dark:divide-gray-700">
          <div
            v-for="row in rows"
            :key="row.id_proyecto"
            class="flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
            @click="openProject(row as Record<string, unknown>)"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <p class="text-sm font-semibold text-gray-800 dark:text-gray-200">{{ row.nombre }}</p>
                <Badge :variant="estadoVariant[row.estado as EstadoProyecto] ?? 'default'" >{{ estadoLabel[row.estado as EstadoProyecto] ?? row.estado }}</Badge>
              </div>
              <p class="text-xs text-gray-400 mt-1">{{ getClientName(Number(row.id_cliente)) }} · Creado {{ row.fecha_creacion }}</p>
            </div>
            <div class="flex items-center gap-3 ml-4">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ row.presupuesto }}</span>
              <button
                v-if="canDeleteProject"
                @click.stop="handleDeleteProyecto(Number(row.id_proyecto))"
                class="p-1.5 text-xs bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
                title="Eliminar proyecto"
              >
                <Trash2 :size="13" />
              </button>
              <ChevronRight :size="16" class="text-gray-400" />
            </div>
          </div>
        </div>
      </Card>
    </div>

    <!-- Task Kanban Board -->
    <div v-else>
      <!-- Project Stats -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div v-for="col in kanbanColumns" :key="col.estado" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3 text-center">
          <p class="text-2xl font-bold text-gray-800 dark:text-white">{{ tareasByEstado[col.estado].length }}</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ col.label }}</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3 text-center">
          <p class="text-sm font-semibold text-cyan-700">{{ formatUSD(projectMetrics?.ingresos_facturados ?? 0) }}</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Ingresos Facturados</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3 text-center">
          <p class="text-sm font-semibold" :class="(projectMetrics?.margen_presupuestario ?? 0) >= 0 ? 'text-emerald-700' : 'text-red-600'">
            {{ formatUSD(projectMetrics?.margen_presupuestario ?? 0) }}
          </p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Margen Presupuestario</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3 text-center">
          <p class="text-sm font-semibold" :class="(projectMetrics?.utilidad_neta_real ?? 0) >= 0 ? 'text-emerald-700' : 'text-red-600'">
            {{ formatUSD(projectMetrics?.utilidad_neta_real ?? 0) }}
          </p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Utilidad Neta Real</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3 text-center">
          <p class="text-sm font-semibold" :class="(projectMetrics?.margen_neto_pct ?? 0) >= 0 ? 'text-emerald-700' : 'text-red-600'">
            {{ (projectMetrics?.margen_neto_pct ?? 0).toFixed(2) }}%
          </p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Margen Neto</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3 text-center">
          <p class="text-sm font-semibold text-blue-700">{{ formatUSD(projectMetrics?.costo_total_operativo ?? 0) }}</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Costo Operativo</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3 text-center">
          <p class="text-sm font-semibold text-amber-700">{{ (projectMetrics?.consumo_presupuesto_pct ?? 0).toFixed(2) }}%</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Consumo Presupuesto</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3 text-center">
          <p class="text-sm font-semibold text-gray-800 dark:text-gray-100">{{ projectMetrics?.tickets_cerrados ?? 0 }}/{{ projectMetrics?.tickets_total ?? 0 }}</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Tickets Cerrados</p>
        </div>
      </div>

      <Card>
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
            <Receipt :size="15" class="text-cyan-600" />
            Cotizaciones y Facturas Vinculadas
          </h3>
          <Button size="sm" variant="secondary" @click="openVentasFromProyecto">Ir a Ventas</Button>
        </div>

        <div v-if="cotizacionesLoading" class="text-sm text-gray-500 py-2">Cargando cotizaciones vinculadas…</div>
        <div v-else-if="cotizacionesProyecto.length === 0" class="text-sm text-gray-400 py-2">No hay cotizaciones vinculadas a este proyecto.</div>
        <div v-else class="space-y-2">
          <div
            v-for="item in cotizacionesProyecto"
            :key="item.id_cotizacion"
            class="flex items-center justify-between border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2"
          >
            <div>
              <p class="text-sm font-medium text-gray-800 dark:text-gray-200">{{ item.numero }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400">
                {{ estadoCotizacionLabel[item.estado] ?? item.estado }} · {{ new Date(item.fecha_creacion).toLocaleDateString('en-US') }}
                <span v-if="item.numero_factura"> · Factura {{ item.numero_factura }}</span>
              </p>
            </div>
            <div class="text-right">
              <p class="text-sm font-semibold text-cyan-700">{{ formatUSD(Number(item.total ?? 0)) }}</p>
            </div>
          </div>
        </div>
      </Card>

      <!-- Kanban -->
      <div v-if="tareasLoading" class="flex justify-center py-8">
        <svg class="animate-spin h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div
          v-for="col in kanbanColumns"
          :key="col.estado"
          class="bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700 min-h-[300px]"
        >
          <!-- Column header -->
          <div class="flex items-center gap-2 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <component :is="col.icon" :size="16" :class="col.color" />
            <span class="text-sm font-semibold text-gray-700 dark:text-gray-300">{{ col.label }}</span>
            <span class="ml-auto text-xs bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded-full">
              {{ tareasByEstado[col.estado].length }}
            </span>
          </div>

          <!-- Task cards -->
          <div class="p-3 space-y-2">
            <div
              v-if="tareasByEstado[col.estado].length === 0"
              class="text-center py-6 text-xs text-gray-400"
            >
              Sin tareas
            </div>
            <div
              v-for="tarea in tareasByEstado[col.estado]"
              :key="tarea.id_tarea"
              class="bg-white dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 p-3 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
              :class="isOverdue(tarea) ? 'border-l-4 border-l-red-400' : ''"
              @click="openTareaDetail(tarea)"
            >
              <!-- Priority indicator + Title -->
              <div class="flex items-start gap-2 mb-2">
                <Flag :size="13" :class="[prioridadColor[tarea.prioridad] ?? 'text-gray-400', 'mt-0.5 shrink-0']" />
                <p class="text-sm font-medium text-gray-800 dark:text-gray-200 leading-snug">{{ tarea.titulo }}</p>
              </div>

              <p v-if="tarea.descripcion" class="text-xs text-gray-500 dark:text-gray-400 mb-2 line-clamp-2 ml-5">{{ tarea.descripcion }}</p>

              <!-- Tags -->
              <div v-if="tarea.etiquetas" class="flex flex-wrap gap-1 mb-2 ml-5">
                <span
                  v-for="tag in parseEtiquetas(tarea.etiquetas)"
                  :key="tag"
                  class="text-xs bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded"
                >
                  {{ tag }}
                </span>
              </div>

              <div class="flex items-center justify-between mt-2 pt-2 border-t border-gray-50 dark:border-gray-600">
                <div class="flex items-center gap-2 text-xs text-gray-400">
                  <span v-if="tarea.id_asignado" class="flex items-center gap-1">
                    <User :size="11" />
                    {{ getUserName(tarea.id_asignado) }}
                  </span>
                  <span v-if="tarea.fecha_vencimiento" :class="['flex items-center gap-1', isOverdue(tarea) ? 'text-red-500 font-medium' : '']">
                    <Calendar :size="11" />
                    {{ new Date(tarea.fecha_vencimiento).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
                  </span>
                  <span v-if="tarea.horas_estimadas" class="flex items-center gap-1">
                    <Clock :size="10" />
                    {{ tarea.horas_reales }}/{{ tarea.horas_estimadas }}h
                  </span>
                </div>
                <div class="flex gap-1 ml-auto">
                  <button
                    v-for="nextCol in kanbanColumns.filter((c) => c.estado !== tarea.estado)"
                    :key="nextCol.estado"
                    @click.stop="updateTareaEstado(tarea.id_tarea, nextCol.estado)"
                    class="text-xs px-2 py-0.5 rounded border border-gray-200 dark:border-gray-500 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                  >
                    → {{ nextCol.label.split(' ')[0] }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Project Modal -->
    <Modal :open="showCreateModal" title="Nuevo Proyecto" size="lg" @close="showCreateModal = false; resetForm()">
      <form @submit.prevent="handleCreate" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Cliente *</label>
            <select v-model.number="form.id_cliente" required class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100">
              <option :value="0">Selecciona un cliente</option>
              <option v-for="cliente in clienteStore.clientes" :key="cliente.id_cliente" :value="cliente.id_cliente">
                {{ cliente.empresa?.razon_social ?? cliente.cliente_b2c?.nombre_completo }}
              </option>
            </select>
            <p v-if="selectedCliente" class="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {{ selectedCliente.tipo_cliente }} · {{ selectedCliente.estado }}
            </p>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Estado</label>
            <select v-model="form.estado" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100">
              <option v-for="(label, val) in estadoLabel" :key="val" :value="val">{{ label }}</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nombre del Proyecto *</label>
          <input v-model="form.nombre" required type="text" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Descripción</label>
          <textarea v-model="form.descripcion" rows="3" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none dark:bg-gray-700 dark:text-gray-100" />
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Presupuesto ($)</label>
            <input v-model="form.presupuesto" type="number" min="0" step="0.01" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Fecha Inicio</label>
            <input v-model="form.fecha_inicio" type="date" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Fecha Fin</label>
            <input v-model="form.fecha_fin" type="date" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
          </div>
        </div>
        <p v-if="formError" class="text-sm text-red-600 bg-red-50 dark:bg-red-900/30 px-3 py-2 rounded-lg">{{ formError }}</p>
        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" @click="showCreateModal = false; resetForm()">Cancelar</Button>
          <Button type="submit" :loading="saving">Crear Proyecto</Button>
        </div>
      </form>
    </Modal>

    <!-- Create Task Modal - JIRA-style -->
    <Modal :open="showTareaModal" title="Nueva Tarea" size="lg" @close="showTareaModal = false; resetTareaForm()">
      <form @submit.prevent="handleCreateTarea" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Título *</label>
          <input v-model="tareaForm.titulo" required type="text" placeholder="¿Qué hay que hacer?" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Descripción</label>
          <textarea v-model="tareaForm.descripcion" rows="3" placeholder="Describe los criterios de aceptación, pasos, contexto..." class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none dark:bg-gray-700 dark:text-gray-100" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Estado</label>
            <select v-model="tareaForm.estado" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100">
              <option value="pendiente">Pendiente</option>
              <option value="en_progreso">En Progreso</option>
              <option value="completado">Completado</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Prioridad</label>
            <select v-model="tareaForm.prioridad" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100">
              <option value="critica">🔴 Crítica</option>
              <option value="alta">🟠 Alta</option>
              <option value="media">🔵 Media</option>
              <option value="baja">⚪ Baja</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Asignado a</label>
            <select v-model.number="tareaForm.id_asignado" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white dark:bg-gray-700 dark:text-gray-100">
              <option :value="null">— Sin asignar —</option>
              <option v-for="u in usuariosStore.usuarios" :key="u.id_usuario" :value="u.id_usuario">
                {{ u.nombre_completo ?? u.username }} ({{ u.rol }})
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Fecha de Vencimiento</label>
            <input v-model="tareaForm.fecha_vencimiento" type="date" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Horas Estimadas</label>
            <input v-model="tareaForm.horas_estimadas" type="number" min="0" step="0.5" class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" placeholder="ej. 8" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              <Tag :size="13" class="inline mr-1" />
              Etiquetas (separadas por coma)
            </label>
            <input v-model="tareaForm.etiquetas" type="text" placeholder="backend, urgente, bug..." class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none dark:bg-gray-700 dark:text-gray-100" />
          </div>
        </div>
        <p v-if="formError" class="text-sm text-red-600 bg-red-50 dark:bg-red-900/30 px-3 py-2 rounded-lg">{{ formError }}</p>
        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" @click="showTareaModal = false; resetTareaForm()">Cancelar</Button>
          <Button type="submit" :loading="saving">Crear Tarea</Button>
        </div>
      </form>
    </Modal>

    <!-- Task Detail Modal -->
    <Modal :open="showTareaDetailModal" :title="selectedTarea?.titulo ?? 'Tarea'" size="lg" @close="showTareaDetailModal = false; selectedTarea = null">
      <div v-if="selectedTarea" class="space-y-4 text-sm">
        <div class="flex items-center gap-3">
          <Badge :variant="prioridadVariant[selectedTarea.prioridad] ?? 'default'">
            <Flag :size="11" class="mr-1" />
            {{ selectedTarea.prioridad.charAt(0).toUpperCase() + selectedTarea.prioridad.slice(1) }}
          </Badge>
          <Badge variant="info">{{ selectedTarea.estado.replace('_', ' ') }}</Badge>
          <span v-if="isOverdue(selectedTarea)" class="text-xs text-red-500 font-medium">⚠ Vencida</span>
        </div>

        <div v-if="selectedTarea.descripcion" class="text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          {{ selectedTarea.descripcion }}
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <User :size="14" />
            <span><strong>Asignado:</strong> {{ getUserName(selectedTarea.id_asignado) }}</span>
          </div>
          <div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <Calendar :size="14" />
            <span><strong>Vencimiento:</strong> {{ selectedTarea.fecha_vencimiento ? new Date(selectedTarea.fecha_vencimiento).toLocaleDateString('es-EC') : '—' }}</span>
          </div>
          <div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <Clock :size="14" />
            <span><strong>Horas:</strong> {{ selectedTarea.horas_reales }}/{{ selectedTarea.horas_estimadas ?? '—' }}h</span>
          </div>
          <div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <FolderOpen :size="14" />
            <span><strong>Creada:</strong> {{ new Date(selectedTarea.fecha_creacion).toLocaleDateString('es-EC') }}</span>
          </div>
        </div>

        <div v-if="selectedTarea.etiquetas">
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="tag in parseEtiquetas(selectedTarea.etiquetas)"
              :key="tag"
              class="text-xs bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 px-2 py-1 rounded-full"
            >
              <Tag :size="11" class="inline mr-1" />{{ tag }}
            </span>
          </div>
        </div>

        <div class="flex justify-between items-center pt-2">
          <div>
            <Button
              v-if="selectedTarea"
              variant="danger"
              size="sm"
              @click="deleteTarea(selectedTarea.id_tarea)"
            >
              <Trash2 :size="14" class="mr-1" />
              Eliminar
            </Button>
          </div>
          <div class="flex gap-2">
            <Button
              v-for="col in kanbanColumns.filter((c) => c.estado !== selectedTarea?.estado)"
              :key="col.estado"
              variant="secondary"
              size="sm"
              @click="updateTareaEstado(selectedTarea.id_tarea, col.estado); showTareaDetailModal = false"
            >
              → {{ col.label }}
            </Button>
            <Button @click="showTareaDetailModal = false">Cerrar</Button>
          </div>
        </div>
      </div>
    </Modal>
  </div>
</template>

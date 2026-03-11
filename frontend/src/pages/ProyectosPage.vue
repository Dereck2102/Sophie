<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Plus, FolderOpen, ChevronRight, CheckSquare, Clock, Circle, ArrowLeft } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import api from '../services/api'
import type { Proyecto, Tarea, EstadoProyecto, EstadoTarea } from '../types'

const proyectos = ref<Proyecto[]>([])
const tareas = ref<Tarea[]>([])
const loading = ref(true)
const selectedProject = ref<Proyecto | null>(null)
const tareasLoading = ref(false)
const showCreateModal = ref(false)
const showTareaModal = ref(false)
const saving = ref(false)
const formError = ref<string | null>(null)

const form = ref({
  id_cliente: 0,
  nombre: '',
  descripcion: '',
  estado: 'propuesta' as EstadoProyecto,
  presupuesto: '',
})

const tareaForm = ref({
  titulo: '',
  descripcion: '',
  estado: 'pendiente' as EstadoTarea,
  horas_estimadas: '',
})

const estadoVariant: Record<EstadoProyecto, 'default' | 'info' | 'success' | 'warning' | 'danger'> = {
  propuesta: 'info', en_progreso: 'warning', pausado: 'default', completado: 'success', cancelado: 'danger',
}
const estadoLabel: Record<EstadoProyecto, string> = {
  propuesta: 'Propuesta', en_progreso: 'En Progreso', pausado: 'Pausado', completado: 'Completado', cancelado: 'Cancelado',
}

const rows = computed(() =>
  proyectos.value.map((p) => ({
    ...p,
    id: p.id_proyecto,
    presupuesto: p.presupuesto ? `S/ ${Number(p.presupuesto).toFixed(2)}` : '—',
    fecha_creacion: new Date(p.fecha_creacion).toLocaleDateString('es-PE'),
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

onMounted(async () => {
  try {
    const { data } = await api.get<Proyecto[]>('/api/v1/proyectos/')
    proyectos.value = data
  } finally {
    loading.value = false
  }
})

async function openProject(row: Record<string, unknown>): Promise<void> {
  const p = proyectos.value.find((x) => x.id_proyecto === row.id_proyecto)
  if (!p) return
  selectedProject.value = p
  tareasLoading.value = true
  tareas.value = []
  try {
    const { data } = await api.get<Tarea[]>(`/api/v1/proyectos/${p.id_proyecto}/tareas`)
    tareas.value = data
  } finally {
    tareasLoading.value = false
  }
}

async function updateTareaEstado(id: number, estado: EstadoTarea): Promise<void> {
  try {
    await api.patch<Tarea>(`/api/v1/proyectos/tareas/${id}`, { estado })
    const idx = tareas.value.findIndex((t) => t.id_tarea === id)
    if (idx >= 0) {
      const t = tareas.value[idx]
      if (t) t.estado = estado
    }
  } catch {
    // silently ignore
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
    const { data } = await api.post<Tarea>(`/api/v1/proyectos/${selectedProject.value.id_proyecto}/tareas`, {
      titulo: tareaForm.value.titulo,
      descripcion: tareaForm.value.descripcion || undefined,
      estado: tareaForm.value.estado,
      horas_estimadas: tareaForm.value.horas_estimadas ? Number(tareaForm.value.horas_estimadas) : undefined,
    })
    tareas.value.push(data)
    showTareaModal.value = false
    tareaForm.value = { titulo: '', descripcion: '', estado: 'pendiente', horas_estimadas: '' }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail ?? 'Error al crear tarea'
  } finally {
    saving.value = false
  }
}

function resetForm(): void {
  form.value = { id_cliente: 0, nombre: '', descripcion: '', estado: 'propuesta', presupuesto: '' }
  formError.value = null
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
        <button v-else @click="selectedProject = null; tareas = []" class="p-2 hover:bg-gray-100 rounded-lg transition-colors">
          <ArrowLeft :size="20" />
        </button>
        <div>
          <h1 class="text-2xl font-bold text-gray-900">
            {{ selectedProject ? selectedProject.nombre : 'Proyectos & Asesoría' }}
          </h1>
          <p class="text-gray-500 text-sm mt-1">
            {{ selectedProject ? `Cliente #${selectedProject.id_cliente} · ${estadoLabel[selectedProject.estado]}` : 'Gestión de proyectos de software y ciberseguridad' }}
          </p>
        </div>
      </div>
      <div class="flex gap-2">
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
        <div v-else-if="rows.length === 0" class="text-center py-12 text-gray-400 text-sm">
          No hay proyectos registrados
        </div>
        <div v-else class="divide-y divide-gray-50">
          <div
            v-for="row in rows"
            :key="row.id_proyecto"
            class="flex items-center justify-between px-5 py-4 hover:bg-gray-50 cursor-pointer transition-colors"
            @click="openProject(row as Record<string, unknown>)"
          >
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <p class="text-sm font-semibold text-gray-800">{{ row.nombre }}</p>
                <Badge :variant="estadoVariant[row.estado as EstadoProyecto] ?? 'default'" >{{ estadoLabel[row.estado as EstadoProyecto] ?? row.estado }}</Badge>
              </div>
              <p class="text-xs text-gray-400 mt-1">Cliente #{{ row.id_cliente }} · Creado {{ row.fecha_creacion }}</p>
            </div>
            <div class="flex items-center gap-3 ml-4">
              <span class="text-sm font-medium text-gray-700">{{ row.presupuesto }}</span>
              <ChevronRight :size="16" class="text-gray-400" />
            </div>
          </div>
        </div>
      </Card>
    </div>

    <!-- Task Kanban Board -->
    <div v-else>
      <!-- Project Stats -->
      <div class="grid grid-cols-3 gap-4 mb-4">
        <div v-for="col in kanbanColumns" :key="col.estado" class="bg-white rounded-xl border border-gray-200 p-3 text-center">
          <p class="text-2xl font-bold text-gray-800">{{ tareasByEstado[col.estado].length }}</p>
          <p class="text-xs text-gray-500 mt-1">{{ col.label }}</p>
        </div>
      </div>

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
          class="bg-gray-50 rounded-xl border border-gray-200 min-h-[300px]"
        >
          <!-- Column header -->
          <div class="flex items-center gap-2 px-4 py-3 border-b border-gray-200">
            <component :is="col.icon" :size="16" :class="col.color" />
            <span class="text-sm font-semibold text-gray-700">{{ col.label }}</span>
            <span class="ml-auto text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">
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
              class="bg-white rounded-lg border border-gray-200 p-3 shadow-sm hover:shadow-md transition-shadow"
            >
              <p class="text-sm font-medium text-gray-800">{{ tarea.titulo }}</p>
              <p v-if="tarea.descripcion" class="text-xs text-gray-500 mt-1 line-clamp-2">{{ tarea.descripcion }}</p>
              <div class="flex items-center justify-between mt-2 pt-2 border-t border-gray-50">
                <span v-if="tarea.horas_estimadas" class="text-xs text-gray-400">
                  <Clock :size="10" class="inline mr-0.5" />
                  {{ tarea.horas_reales }}/{{ tarea.horas_estimadas }}h
                </span>
                <div class="flex gap-1 ml-auto">
                  <button
                    v-for="nextCol in kanbanColumns.filter((c) => c.estado !== tarea.estado)"
                    :key="nextCol.estado"
                    @click="updateTareaEstado(tarea.id_tarea, nextCol.estado)"
                    class="text-xs px-2 py-0.5 rounded border border-gray-200 text-gray-500 hover:bg-gray-100 transition-colors"
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
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">ID Cliente *</label>
          <input v-model.number="form.id_cliente" required type="number" min="1" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Nombre del Proyecto *</label>
          <input v-model="form.nombre" required type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
          <textarea v-model="form.descripcion" rows="3" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Estado</label>
            <select v-model="form.estado" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white">
              <option v-for="(label, val) in estadoLabel" :key="val" :value="val">{{ label }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Presupuesto (S/)</label>
            <input v-model="form.presupuesto" type="number" min="0" step="0.01" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>
        </div>
        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>
        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" @click="showCreateModal = false; resetForm()">Cancelar</Button>
          <Button type="submit" :loading="saving">Crear Proyecto</Button>
        </div>
      </form>
    </Modal>

    <!-- Create Task Modal -->
    <Modal :open="showTareaModal" title="Nueva Tarea" size="md" @close="showTareaModal = false; formError = null">
      <form @submit.prevent="handleCreateTarea" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Título *</label>
          <input v-model="tareaForm.titulo" required type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
          <textarea v-model="tareaForm.descripcion" rows="2" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none resize-none" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Estado Inicial</label>
            <select v-model="tareaForm.estado" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white">
              <option value="pendiente">Pendiente</option>
              <option value="en_progreso">En Progreso</option>
              <option value="completado">Completado</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Horas Estimadas</label>
            <input v-model="tareaForm.horas_estimadas" type="number" min="0" step="0.5" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" placeholder="ej. 8" />
          </div>
        </div>
        <p v-if="formError" class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{{ formError }}</p>
        <div class="flex justify-end gap-3 pt-2">
          <Button variant="secondary" type="button" @click="showTareaModal = false">Cancelar</Button>
          <Button type="submit" :loading="saving">Crear Tarea</Button>
        </div>
      </form>
    </Modal>
  </div>
</template>


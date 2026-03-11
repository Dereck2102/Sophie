<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Plus, FolderOpen } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import Badge from '../components/ui/Badge.vue'
import Button from '../components/ui/Button.vue'
import Modal from '../components/ui/Modal.vue'
import api from '../services/api'

interface Proyecto {
  id_proyecto: number
  id_cliente: number
  nombre: string
  descripcion?: string
  estado: 'propuesta' | 'en_progreso' | 'pausado' | 'completado' | 'cancelado'
  presupuesto?: number
  fecha_inicio?: string
  fecha_fin?: string
  fecha_creacion: string
}

const proyectos = ref<Proyecto[]>([])
const loading = ref(true)
const showCreateModal = ref(false)
const saving = ref(false)
const formError = ref<string | null>(null)

const form = ref({
  id_cliente: 0,
  nombre: '',
  descripcion: '',
  estado: 'propuesta' as Proyecto['estado'],
  presupuesto: '',
})

const columns = [
  { key: 'nombre', label: 'Proyecto' },
  { key: 'id_cliente', label: 'Cliente' },
  { key: 'estado', label: 'Estado', class: 'w-36' },
  { key: 'presupuesto', label: 'Presupuesto', class: 'w-36' },
  { key: 'fecha_creacion', label: 'Creado', class: 'w-32' },
]

const estadoVariant: Record<string, 'default' | 'info' | 'success' | 'warning' | 'danger'> = {
  propuesta: 'info',
  en_progreso: 'warning',
  pausado: 'default',
  completado: 'success',
  cancelado: 'danger',
}

const rows = computed(() =>
  proyectos.value.map((p) => ({
    ...p,
    id: p.id_proyecto,
    presupuesto: p.presupuesto ? `S/ ${Number(p.presupuesto).toFixed(2)}` : '—',
    fecha_creacion: new Date(p.fecha_creacion).toLocaleDateString('es-PE'),
  }))
)

onMounted(async () => {
  try {
    const { data } = await api.get<Proyecto[]>('/api/v1/proyectos/')
    proyectos.value = data
  } finally {
    loading.value = false
  }
})

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

function resetForm(): void {
  form.value = { id_cliente: 0, nombre: '', descripcion: '', estado: 'propuesta', presupuesto: '' }
  formError.value = null
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="p-2 bg-blue-600 rounded-xl">
          <FolderOpen class="text-white" :size="22" />
        </div>
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Proyectos & Asesoría</h1>
          <p class="text-gray-500 text-sm mt-1">Gestión de proyectos de software y ciberseguridad</p>
        </div>
      </div>
      <Button @click="showCreateModal = true">
        <Plus :size="16" class="mr-2" />
        Nuevo Proyecto
      </Button>
    </div>

    <Card :padding="false">
      <Table :columns="columns" :rows="rows" :loading="loading">
        <template #estado="{ value }">
          <Badge :variant="estadoVariant[String(value)] ?? 'default'">{{ value }}</Badge>
        </template>
      </Table>
    </Card>

    <!-- Create Modal -->
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
              <option value="propuesta">Propuesta</option>
              <option value="en_progreso">En Progreso</option>
              <option value="pausado">Pausado</option>
              <option value="completado">Completado</option>
              <option value="cancelado">Cancelado</option>
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
  </div>
</template>

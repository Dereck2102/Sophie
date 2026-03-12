<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import api from '../services/api'
import type { AuditoriaLog } from '../types'

const logs = ref<Record<string, unknown>[]>([])
const loading = ref(false)
const modulo = ref('')
const usuarioId = ref('')

const columns = [
  { key: 'fecha', label: 'Fecha', class: 'w-48' },
  { key: 'accion', label: 'Acción' },
  { key: 'modulo', label: 'Módulo', class: 'w-32' },
  { key: 'id_usuario', label: 'Usuario', class: 'w-24' },
  { key: 'ip_origen', label: 'IP', class: 'w-32' },
]

async function loadLogs(): Promise<void> {
  loading.value = true
  try {
    const { data } = await api.get<AuditoriaLog[]>('/api/v1/admin/auditoria', {
      params: {
        modulo: modulo.value || undefined,
        id_usuario: usuarioId.value ? Number(usuarioId.value) : undefined,
      },
    })
    logs.value = data.map((item) => ({
      ...item,
      id: item.id_log,
      fecha: new Date(item.fecha).toLocaleString('es-EC'),
    }))
  } finally {
    loading.value = false
  }
}

onMounted(loadLogs)
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Auditoría del Sistema</h1>
      <p class="text-gray-500 text-sm mt-1">Trazabilidad completa de acciones, accesos y rendimiento.</p>
    </div>

    <Card :padding="false">
      <div class="p-4 border-b border-gray-100 flex flex-wrap gap-3 items-end">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Módulo</label>
          <input v-model="modulo" type="text" class="px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Usuario ID</label>
          <input v-model="usuarioId" type="number" min="1" class="px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <button @click="loadLogs" class="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700">Filtrar</button>
      </div>
      <Table :columns="columns" :rows="logs" :loading="loading" />
    </Card>
  </div>
</template>
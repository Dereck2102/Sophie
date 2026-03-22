<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Badge from '../components/ui/Badge.vue'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import api from '../services/api'
import type { AuditoriaLog } from '../types'

const logs = ref<Record<string, unknown>[]>([])
const loading = ref(false)

const searchText = ref('')
const modulo = ref('')
const usuarioId = ref('')
const empresaId = ref('')
const accionTipo = ref('')
const accionNombre = ref('')
const ipOrigen = ref('')
const fechaDesde = ref('')
const fechaHasta = ref('')

const actionTypeOptions = [
  { value: '', label: 'Todas las acciones' },
  { value: 'login', label: 'Login' },
  { value: 'login_failed', label: 'Login fallido' },
  { value: 'logout', label: 'Logout' },
  { value: 'crear', label: 'Crear' },
  { value: 'modificar', label: 'Modificar / Editar' },
  { value: 'eliminar', label: 'Eliminar' },
  { value: 'buscar', label: 'Buscar / Filtrar' },
  { value: 'consultar', label: 'Consultar' },
]

const quickStats = computed(() => {
  const total = logs.value.length
  const byType = logs.value.reduce<Record<string, number>>((acc, item) => {
    const key = String(item.accion_tipo || 'otros')
    acc[key] = (acc[key] ?? 0) + 1
    return acc
  }, {})
  return {
    total,
    logins: byType.login ?? 0,
    creates: byType.crear ?? 0,
    updates: byType.modificar ?? 0,
    deletes: byType.eliminar ?? 0,
  }
})

const columns = [
  { key: 'fecha', label: 'Fecha', class: 'w-48' },
  { key: 'accion_nombre', label: 'Acción', class: 'w-56' },
  { key: 'accion_tipo', label: 'Tipo', class: 'w-40' },
  { key: 'modulo', label: 'Módulo', class: 'w-32' },
  { key: 'usuario', label: 'Usuario', class: 'w-56' },
  { key: 'empresa', label: 'Empresa', class: 'w-56' },
  { key: 'ip_origen', label: 'IP', class: 'w-32' },
  { key: 'ubicacion_aprox', label: 'Ubicación', class: 'w-56' },
  { key: 'detalle_resumen', label: 'Detalle' },
]

function toIsoLocalDateTime(value: string, endOfMinute = false): string | undefined {
  if (!value) return undefined
  const suffix = endOfMinute ? ':59' : ':00'
  return `${value}${suffix}`
}

function toFriendlyActionName(log: AuditoriaLog): string {
  return log.accion_nombre || log.accion
}

function toFriendlyActionType(log: AuditoriaLog): string {
  return log.accion_tipo || 'otros'
}

function summarizeDetail(log: AuditoriaLog): string {
  const statusCode = (log.detalle?.status_code as number | undefined) ?? undefined
  const duration = (log.detalle?.duration_ms as number | undefined) ?? undefined
  const route = log.ruta ?? '-'
  return `${statusCode ?? '-'} · ${duration ?? '-'} ms · ${route}`
}

function actionBadgeVariant(actionType: string): 'success' | 'warning' | 'danger' | 'info' | 'default' {
  if (['login', 'crear'].includes(actionType)) return 'success'
  if (['modificar', 'buscar', 'consultar'].includes(actionType)) return 'info'
  if (['eliminar', 'login_failed'].includes(actionType)) return 'danger'
  if (actionType === 'logout') return 'warning'
  return 'default'
}

async function loadLogs(): Promise<void> {
  loading.value = true
  try {
    const { data } = await api.get<AuditoriaLog[]>('/api/v1/admin/auditoria', {
      params: {
        q: searchText.value || undefined,
        modulo: modulo.value || undefined,
        id_usuario: usuarioId.value ? Number(usuarioId.value) : undefined,
        id_cliente: empresaId.value ? Number(empresaId.value) : undefined,
        accion_tipo: accionTipo.value || undefined,
        accion_nombre: accionNombre.value || undefined,
        ip_origen: ipOrigen.value || undefined,
        fecha_desde: toIsoLocalDateTime(fechaDesde.value),
        fecha_hasta: toIsoLocalDateTime(fechaHasta.value, true),
      },
    })
    logs.value = data.map((item) => ({
      ...item,
      id: item.id_log,
      fecha: new Date(item.fecha).toLocaleString('es-EC'),
      accion_nombre: toFriendlyActionName(item),
      accion_tipo: toFriendlyActionType(item),
      usuario: item.id_usuario
        ? `${item.usuario_nombre || item.usuario_username || 'Usuario'} (#${item.id_usuario})`
        : 'Sistema',
      empresa: item.id_cliente
        ? `${item.empresa_nombre || 'Empresa'} (#${item.id_cliente})`
        : 'Sin empresa',
      ubicacion_aprox: item.ubicacion_aprox || [item.ciudad_origen, item.pais_origen].filter(Boolean).join(', ') || 'No disponible',
      detalle_resumen: summarizeDetail(item),
    }))
  } finally {
    loading.value = false
  }
}

function resetFilters(): void {
  searchText.value = ''
  modulo.value = ''
  usuarioId.value = ''
  empresaId.value = ''
  accionTipo.value = ''
  accionNombre.value = ''
  ipOrigen.value = ''
  fechaDesde.value = ''
  fechaHasta.value = ''
  void loadLogs()
}

onMounted(loadLogs)
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Auditoría del Sistema</h1>
      <p class="text-gray-500 text-sm mt-1">Logs comprensibles de acceso, cambios y operaciones con filtros avanzados.</p>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
      <Card>
        <p class="text-xs text-gray-500">Total</p>
        <p class="text-xl font-bold text-gray-900">{{ quickStats.total }}</p>
      </Card>
      <Card>
        <p class="text-xs text-gray-500">Logins</p>
        <p class="text-xl font-bold text-emerald-700">{{ quickStats.logins }}</p>
      </Card>
      <Card>
        <p class="text-xs text-gray-500">Creaciones</p>
        <p class="text-xl font-bold text-blue-700">{{ quickStats.creates }}</p>
      </Card>
      <Card>
        <p class="text-xs text-gray-500">Modificaciones</p>
        <p class="text-xl font-bold text-indigo-700">{{ quickStats.updates }}</p>
      </Card>
      <Card>
        <p class="text-xs text-gray-500">Eliminaciones</p>
        <p class="text-xl font-bold text-red-700">{{ quickStats.deletes }}</p>
      </Card>
    </div>

    <Card :padding="false">
      <div class="p-4 border-b border-gray-100 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 items-end">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Texto</label>
          <input v-model="searchText" type="text" placeholder="usuario, empresa, ruta, acción" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Módulo</label>
          <input v-model="modulo" type="text" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Usuario (ID)</label>
          <input v-model="usuarioId" type="number" min="1" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Empresa (ID)</label>
          <input v-model="empresaId" type="number" min="1" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Tipo de acción</label>
          <select v-model="accionTipo" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white">
            <option v-for="option in actionTypeOptions" :key="option.value || 'all'" :value="option.value">{{ option.label }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Nombre de acción</label>
          <input v-model="accionNombre" type="text" placeholder="crear, editar, login..." class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">IP origen</label>
          <input v-model="ipOrigen" type="text" placeholder="192.168.1.10" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Desde</label>
          <input v-model="fechaDesde" type="datetime-local" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
          <input v-model="fechaHasta" type="datetime-local" class="w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div class="xl:col-span-4 flex gap-2 justify-end">
          <button @click="resetFilters" class="px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50">Limpiar</button>
          <button @click="loadLogs" class="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700">Aplicar filtros</button>
        </div>
      </div>
      <Table :columns="columns" :rows="logs" :loading="loading" empty-text="No hay logs para los filtros seleccionados">
        <template #accion_tipo="{ value }">
          <Badge :variant="actionBadgeVariant(String(value))">{{ value }}</Badge>
        </template>
        <template #ip_origen="{ value }">
          <span class="font-mono text-xs">{{ value || '—' }}</span>
        </template>
        <template #detalle_resumen="{ value, row }">
          <div class="space-y-0.5">
            <p class="text-xs text-gray-800">{{ value }}</p>
            <p class="text-[11px] text-gray-500">{{ (row as Record<string, unknown>).user_agent || 'Sin user-agent' }}</p>
          </div>
        </template>
      </Table>
    </Card>
  </div>
</template>
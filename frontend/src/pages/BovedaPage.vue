<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Lock } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Table from '../components/ui/Table.vue'
import api from '../services/api'

interface Credencial {
  id_credencial: number
  id_empresa: number
  nombre: string
  usuario_acceso?: string
  url?: string
  notas?: string
}

const credenciales = ref<Credencial[]>([])
const loading = ref(true)
const mfaRequired = ref(false)

const columns = [
  { key: 'id_empresa', label: 'Empresa' },
  { key: 'nombre', label: 'Nombre' },
  { key: 'usuario_acceso', label: 'Usuario' },
  { key: 'url', label: 'URL' },
]

onMounted(async () => {
  try {
    const { data } = await api.get<Credencial[]>('/api/v1/boveda/')
    credenciales.value = data
  } catch (e: unknown) {
    const err = e as { response?: { status?: number } }
    if (err.response?.status === 403) mfaRequired.value = true
  } finally {
    loading.value = false
  }
})


</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3">
      <div class="p-2 bg-gray-800 rounded-xl">
        <Lock class="text-white" :size="22" />
      </div>
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Bóveda de Credenciales</h1>
        <p class="text-gray-500 text-sm mt-1">Credenciales B2B cifradas con AES-256-GCM</p>
      </div>
    </div>

    <div v-if="mfaRequired" class="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-3">
      <span class="text-2xl">🔒</span>
      <div>
        <p class="font-semibold text-amber-800">MFA requerido</p>
        <p class="text-sm text-amber-700">Necesitas tener MFA activo para acceder a la bóveda.</p>
      </div>
    </div>

    <Card :padding="false">
      <Table :columns="columns" :rows="credenciales.map((c) => ({ ...c, id: c.id_credencial }))" :loading="loading">
        <template #url="{ value }">
          <a v-if="value" :href="String(value)" target="_blank" class="text-blue-600 hover:underline text-xs truncate block max-w-[200px]">
            {{ value }}
          </a>
          <span v-else class="text-gray-400">—</span>
        </template>
      </Table>
    </Card>
  </div>
</template>

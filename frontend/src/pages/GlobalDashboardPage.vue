<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Card from '../components/ui/Card.vue'
import api from '../services/api'
import type { GlobalDashboardSummary } from '../types'

const loading = ref(false)
const error = ref<string | null>(null)
const summary = ref<GlobalDashboardSummary | null>(null)

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value)
}

async function loadSummary(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get<GlobalDashboardSummary>('/api/v1/global/dashboard/summary')
    summary.value = data
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo cargar el dashboard global.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadSummary()
})
</script>

<template>
  <div class="space-y-6">
    <section class="rounded-2xl border border-gray-200 bg-white p-5">
      <h2 class="text-xl font-bold text-gray-900">Backoffice Global SOPHIE</h2>
      <p class="text-sm text-gray-600 mt-1">Vista consolidada de empresas, suscripciones y facturación.</p>
    </section>

    <section v-if="loading" class="rounded-2xl border border-gray-200 bg-white p-5 text-gray-500">
      Cargando resumen global...
    </section>
    <section v-else-if="error" class="rounded-2xl border border-red-200 bg-red-50 p-5 text-red-700">
      {{ error }}
    </section>
    <template v-else-if="summary">
      <section class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Empresas totales" subtitle="Registradas">
          <div class="text-2xl font-bold text-gray-900">{{ summary.total_companies }}</div>
        </Card>
        <Card title="Empresas activas" subtitle="Estado ACTIVO">
          <div class="text-2xl font-bold text-emerald-700">{{ summary.active_companies }}</div>
        </Card>
        <Card title="Usuarios" subtitle="Registros totales">
          <div class="text-2xl font-bold text-blue-700">{{ summary.registered_users }}</div>
        </Card>
        <Card title="MRR estimado" subtitle="Ingresos recurrentes">
          <div class="text-2xl font-bold text-indigo-700">{{ formatCurrency(summary.mrr_usd) }}</div>
        </Card>
      </section>

      <section class="grid gap-4 xl:grid-cols-3">
        <Card title="Suscripciones" subtitle="Estado actual">
          <div class="space-y-2 text-sm text-gray-700">
            <p class="flex justify-between"><span>Activas</span><span class="font-semibold">{{ summary.active_subscriptions }}</span></p>
            <p class="flex justify-between"><span>Pendientes</span><span class="font-semibold">{{ summary.pending_subscriptions }}</span></p>
            <p class="flex justify-between"><span>Transacciones pagadas</span><span class="font-semibold">{{ summary.paid_transactions }}</span></p>
          </div>
        </Card>

        <Card title="Estado de empresas" subtitle="Operación">
          <div class="space-y-2 text-sm text-gray-700">
            <p class="flex justify-between"><span>Activas</span><span class="font-semibold">{{ summary.active_companies }}</span></p>
            <p class="flex justify-between"><span>Suspendidas/Inactivas</span><span class="font-semibold">{{ summary.suspended_or_inactive_companies }}</span></p>
            <p class="flex justify-between"><span>Sistema</span><span class="font-semibold uppercase">{{ summary.system_status }}</span></p>
          </div>
        </Card>

        <Card title="Distribución por plan" subtitle="Empresas por tier">
          <div class="space-y-2 text-sm text-gray-700">
            <p v-for="item in summary.plan_breakdown" :key="item.tier" class="flex justify-between">
              <span class="uppercase">{{ item.tier }}</span>
              <span class="font-semibold">{{ item.companies }}</span>
            </p>
            <p v-if="summary.plan_breakdown.length === 0" class="text-gray-400">Sin datos</p>
          </div>
        </Card>
      </section>
    </template>
  </div>
</template>

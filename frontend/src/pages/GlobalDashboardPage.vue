<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from '../components/ui/Button.vue'
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
    <section class="app-surface p-6">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div class="space-y-2">
          <span class="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-sky-700 dark:border-sky-900/60 dark:bg-sky-950/40 dark:text-sky-300">Backoffice Global</span>
          <h2 class="text-2xl font-black text-slate-900 dark:text-slate-100">Control central de SOPHIE</h2>
          <p class="text-sm text-slate-600 dark:text-slate-400 max-w-2xl">Vista consolidada de empresas, suscripciones, facturación y estado operativo del ecosistema.</p>
        </div>
        <Button variant="secondary" @click="loadSummary">Refrescar resumen</Button>
      </div>
    </section>

    <section v-if="loading" class="app-surface p-5 text-slate-500">
      Cargando resumen global...
    </section>
    <section v-else-if="error" class="app-surface border-red-200 bg-red-50 p-5 text-red-700 dark:bg-red-950/30 dark:text-red-300">
      {{ error }}
    </section>
    <template v-else-if="summary">
      <section class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Empresas totales" subtitle="Registradas">
          <div class="text-3xl font-black text-slate-900 dark:text-slate-100">{{ summary.total_companies }}</div>
        </Card>
        <Card title="Empresas activas" subtitle="Estado ACTIVO">
          <div class="text-3xl font-black text-emerald-700">{{ summary.active_companies }}</div>
        </Card>
        <Card title="Usuarios" subtitle="Registros totales">
          <div class="text-3xl font-black text-sky-700">{{ summary.registered_users }}</div>
        </Card>
        <Card title="MRR estimado" subtitle="Ingresos recurrentes">
          <div class="text-3xl font-black text-indigo-700">{{ formatCurrency(summary.mrr_usd) }}</div>
        </Card>
      </section>

      <section class="grid gap-4 xl:grid-cols-3">
        <Card title="Suscripciones" subtitle="Estado actual">
          <div class="space-y-2 text-sm text-slate-700 dark:text-slate-300">
            <p class="flex justify-between"><span>Activas</span><span class="font-semibold">{{ summary.active_subscriptions }}</span></p>
            <p class="flex justify-between"><span>Pendientes</span><span class="font-semibold">{{ summary.pending_subscriptions }}</span></p>
            <p class="flex justify-between"><span>Transacciones pagadas</span><span class="font-semibold">{{ summary.paid_transactions }}</span></p>
          </div>
        </Card>

        <Card title="Estado de empresas" subtitle="Operación">
          <div class="space-y-2 text-sm text-slate-700 dark:text-slate-300">
            <p class="flex justify-between"><span>Activas</span><span class="font-semibold">{{ summary.active_companies }}</span></p>
            <p class="flex justify-between"><span>Suspendidas/Inactivas</span><span class="font-semibold">{{ summary.suspended_or_inactive_companies }}</span></p>
            <p class="flex justify-between"><span>Sistema</span><span class="font-semibold uppercase">{{ summary.system_status }}</span></p>
          </div>
        </Card>

        <Card title="Distribución por plan" subtitle="Empresas por tier">
          <div class="space-y-2 text-sm text-slate-700 dark:text-slate-300">
            <p v-for="item in summary.plan_breakdown" :key="item.tier" class="flex justify-between">
              <span class="uppercase">{{ item.tier }}</span>
              <span class="font-semibold">{{ item.companies }}</span>
            </p>
            <p v-if="summary.plan_breakdown.length === 0" class="text-slate-400">Sin datos</p>
          </div>
        </Card>
      </section>
    </template>
  </div>
</template>

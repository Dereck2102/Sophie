<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api from '../services/api'
import type { PublicLanding } from '../types'

const loading = ref(false)
const error = ref<string | null>(null)
const landing = ref<PublicLanding | null>(null)

const sortedPlans = computed(() => {
  const plans = [...(landing.value?.plans ?? [])]
  const weight: Record<string, number> = { starter: 1, pro: 2, enterprise: 3, custom: 4 }
  return plans.sort((a, b) => (weight[a.tier] ?? 99) - (weight[b.tier] ?? 99))
})

function formatPrice(value?: number | null): string {
  if (value == null) return 'A convenir'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value)
}

async function loadLanding(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get<PublicLanding>('/api/v1/public/landing')
    landing.value = data
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo cargar la capa pública.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadLanding()
})
</script>

<template>
  <div class="min-h-screen bg-slate-950 text-white">
    <section class="max-w-6xl mx-auto px-6 pt-16 pb-10">
      <div class="inline-flex items-center gap-2 rounded-full border border-white/20 px-3 py-1 text-xs text-slate-200">
        SOPHIE · Capa Pública
      </div>
      <h1 class="mt-4 text-4xl md:text-5xl font-extrabold tracking-tight">{{ landing?.platform_name ?? 'SOPHIE ERP' }}</h1>
      <p class="mt-3 text-slate-300 max-w-2xl">Ecosistema de gestión empresarial con arquitectura por capas: pública, global y de empresa.</p>
      <p class="mt-2 text-xs text-slate-400">Versión: {{ landing?.platform_version ?? '1.0.0' }}</p>
    </section>

    <section class="max-w-6xl mx-auto px-6 pb-8">
      <h2 class="text-xl font-semibold mb-4">Capas de la plataforma</h2>
      <div v-if="loading" class="text-slate-300">Cargando...</div>
      <div v-else-if="error" class="text-red-300">{{ error }}</div>
      <div v-else class="grid gap-4 md:grid-cols-3">
        <article v-for="layer in landing?.layers ?? []" :key="layer.key" class="rounded-2xl border border-white/10 bg-white/5 p-4">
          <p class="text-xs uppercase tracking-wider text-slate-400">{{ layer.key }}</p>
          <h3 class="mt-1 font-semibold">{{ layer.name }}</h3>
          <p class="mt-2 text-sm text-slate-300">{{ layer.description }}</p>
        </article>
      </div>
    </section>

    <section class="max-w-6xl mx-auto px-6 pb-16">
      <h2 class="text-xl font-semibold mb-4">Planes</h2>
      <div class="grid gap-4 lg:grid-cols-4 md:grid-cols-2">
        <article
          v-for="plan in sortedPlans"
          :key="plan.key"
          class="rounded-2xl border border-white/10 bg-white p-5 text-slate-800"
        >
          <p class="text-xs uppercase tracking-wider text-slate-500">{{ plan.tier }}</p>
          <h3 class="mt-1 text-lg font-bold">{{ plan.name }}</h3>
          <p class="mt-2 text-sm text-slate-600 min-h-[44px]">{{ plan.description }}</p>
          <div class="mt-3 space-y-1 text-sm">
            <p><span class="text-slate-500">Mensual:</span> <span class="font-semibold">{{ formatPrice(plan.monthly_price_usd) }}</span></p>
            <p><span class="text-slate-500">Anual:</span> <span class="font-semibold">{{ formatPrice(plan.yearly_price_usd) }}</span></p>
          </div>
          <div class="mt-4 pt-3 border-t border-slate-200">
            <p class="text-xs uppercase tracking-wider text-slate-500 mb-2">Módulos</p>
            <div class="flex flex-wrap gap-1.5">
              <span
                v-for="module in plan.modules"
                :key="`${plan.key}-${module}`"
                class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium"
              >
                {{ module }}
              </span>
              <span v-if="plan.modules.length === 0" class="text-xs text-slate-400">Definido por superadmin</span>
            </div>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

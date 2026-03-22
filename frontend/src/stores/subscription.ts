import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import api from '../services/api'
import type { EmpresaSubscription, PublicPlan, Usuario } from '../types'

export type EnterpriseModuleCode = 'E1' | 'E2' | 'E3' | 'E4' | 'E5' | 'E6' | 'E7' | 'E8'

const ALL_ENTERPRISE_MODULES: EnterpriseModuleCode[] = ['E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7', 'E8']

const VIEW_TO_MODULE: Partial<Record<string, EnterpriseModuleCode>> = {
  dashboard: 'E2',
  auditoria: 'E2',
  caja_chica: 'E3',
  ventas: 'E4',
  compras: 'E5',
  taller: 'E8',
  proyectos: 'E6',
  empresas: 'E1',
  usuarios: 'E1',
  configuracion: 'E1',
}

export const useSubscriptionStore = defineStore('subscription', () => {
  const loading = ref(false)
  const initialized = ref(false)
  const current = ref<EmpresaSubscription | null>(null)
  const publicPlans = ref<PublicPlan[]>([])

  const activeModules = computed<EnterpriseModuleCode[]>(() => {
    if (!current.value) return ALL_ENTERPRISE_MODULES

    const plan = publicPlans.value.find((item) => item.tier === current.value?.plan_tier)
    const planModules = (plan?.modules ?? []).filter((item): item is EnterpriseModuleCode =>
      ALL_ENTERPRISE_MODULES.includes(item as EnterpriseModuleCode)
    )

    if (current.value.plan_tier === 'custom') {
      return planModules.length > 0 ? planModules : ALL_ENTERPRISE_MODULES
    }

    return planModules.length > 0 ? planModules : ALL_ENTERPRISE_MODULES
  })

  async function bootstrapForCurrentUser(user: Usuario | null): Promise<void> {
    if (!user || user.rol === 'superadmin' || initialized.value) {
      initialized.value = true
      return
    }

    loading.value = true
    try {
      const [plansRes, currentRes] = await Promise.all([
        api.get<PublicPlan[]>('/api/v1/public/plans'),
        api.get<EmpresaSubscription>('/api/v1/subscriptions/my-company'),
      ])
      publicPlans.value = plansRes.data
      current.value = currentRes.data
    } catch {
      current.value = null
    } finally {
      loading.value = false
      initialized.value = true
    }
  }

  function reset(): void {
    initialized.value = false
    current.value = null
    publicPlans.value = []
  }

  function hasModule(moduleCode: EnterpriseModuleCode): boolean {
    return activeModules.value.includes(moduleCode)
  }

  function hasModuleForView(view: string): boolean {
    const moduleCode = VIEW_TO_MODULE[view]
    if (!moduleCode) return true
    return hasModule(moduleCode)
  }

  return {
    loading,
    initialized,
    current,
    publicPlans,
    activeModules,
    bootstrapForCurrentUser,
    hasModule,
    hasModuleForView,
    reset,
  }
})

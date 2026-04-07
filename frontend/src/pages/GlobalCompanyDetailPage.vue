<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Save, CreditCard, Receipt, Eye, EyeOff, Trash2, Building2 } from 'lucide-vue-next'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import api from '../services/api'
import type {
  BillingCycle,
  EmpresaSubscription,
  GlobalCompany,
  GlobalCompanyUpdate,
  PlanPreset,
  SubscriptionPlanTier,
  SubscriptionStatus,
} from '../types'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const savingCompany = ref(false)
const savingSubscription = ref(false)
const creatingCheckout = ref(false)
const mutatingCompany = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)

const company = ref<GlobalCompany | null>(null)
const plans = ref<PlanPreset[]>([])
const subscriptions = ref<EmpresaSubscription[]>([])

const companyId = computed(() => {
  const parsedCompanyId = Number(route.params.companyId)
  return Number.isFinite(parsedCompanyId) && parsedCompanyId > 0 ? parsedCompanyId : 0
})

const companyForm = ref<GlobalCompanyUpdate>({
  nombre: '',
  branding_nombre: '',
  branding_logo_url: '',
  ruc: '',
})

const subscriptionForm = ref<{
  plan_tier: SubscriptionPlanTier
  billing_cycle: BillingCycle
  status: SubscriptionStatus
  custom_notes: string
  feature_overrides: string
}>({
  plan_tier: 'starter',
  billing_cycle: 'monthly',
  status: 'active',
  custom_notes: '',
  feature_overrides: '',
})

function parseFeatureOverrides(raw: string): string[] {
  return raw
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
}

function applyCompanyForm(item: GlobalCompany): void {
  companyForm.value = {
    nombre: item.nombre,
    branding_nombre: item.branding_nombre ?? '',
    branding_logo_url: item.branding_logo_url ?? '',
    ruc: item.ruc,
  }
}

function applySubscriptionForm(id: number): void {
  const current = subscriptions.value.find((item) => item.id_empresa === id)
  if (!current) {
    subscriptionForm.value = {
      plan_tier: 'starter',
      billing_cycle: 'monthly',
      status: 'pending',
      custom_notes: '',
      feature_overrides: '',
    }
    return
  }

  subscriptionForm.value = {
    plan_tier: current.plan_tier,
    billing_cycle: current.billing_cycle,
    status: current.status,
    custom_notes: current.custom_notes ?? '',
    feature_overrides: current.features.join(', '),
  }
}

function applyPlanPreset(plan: SubscriptionPlanTier): void {
  const preset = plans.value.find((item) => item.plan === plan)
  if (!preset) return
  subscriptionForm.value.plan_tier = plan
  subscriptionForm.value.feature_overrides = preset.features.join(', ')
}

async function loadData(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const [companiesRes, plansRes, subsRes] = await Promise.all([
      api.get<GlobalCompany[]>('/api/v1/global/companies', { params: { limit: 500 } }),
      api.get<PlanPreset[]>('/api/v1/subscriptions/plans'),
      api.get<EmpresaSubscription[]>('/api/v1/admin/subscriptions/companies', { params: { limit: 500 } }),
    ])

    plans.value = plansRes.data
    subscriptions.value = subsRes.data

    const found = companiesRes.data.find((item) => item.id_empresa === companyId.value) ?? null
    company.value = found

    if (!found) {
      error.value = 'Empresa no encontrada'
      return
    }

    applyCompanyForm(found)
    applySubscriptionForm(found.id_empresa)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo cargar la empresa'
  } finally {
    loading.value = false
  }
}

async function saveCompany(): Promise<void> {
  if (!company.value) return
  savingCompany.value = true
  error.value = null
  success.value = null
  try {
    await api.patch(`/api/v1/global/companies/${company.value.id_empresa}`, companyForm.value)
    success.value = 'Empresa actualizada'
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo actualizar la empresa'
  } finally {
    savingCompany.value = false
  }
}

async function saveSubscription(): Promise<void> {
  if (!company.value) return
  savingSubscription.value = true
  error.value = null
  success.value = null
  try {
    await api.put(`/api/v1/admin/subscriptions/companies/${company.value.id_empresa}`, {
      plan_tier: subscriptionForm.value.plan_tier,
      billing_cycle: subscriptionForm.value.billing_cycle,
      status: subscriptionForm.value.status,
      custom_notes: subscriptionForm.value.custom_notes || null,
      feature_overrides: parseFeatureOverrides(subscriptionForm.value.feature_overrides),
    })
    success.value = 'Suscripción actualizada'
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo actualizar la suscripción'
  } finally {
    savingSubscription.value = false
  }
}

async function createCheckout(): Promise<void> {
  if (!company.value) return
  creatingCheckout.value = true
  error.value = null
  success.value = null
  try {
    const { data } = await api.post<{ id_pago: number; detail: string; checkout_url?: string | null }>('/api/v1/subscriptions/checkout', {
      plan: subscriptionForm.value.plan_tier,
      billing_cycle: subscriptionForm.value.billing_cycle,
      id_empresa: company.value.id_empresa,
      custom_requirements: subscriptionForm.value.plan_tier === 'custom' ? subscriptionForm.value.custom_notes : undefined,
    })
    success.value = `${data.detail} #${data.id_pago}`
    if (data.checkout_url) {
      window.open(data.checkout_url, '_blank', 'noopener,noreferrer')
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo generar checkout'
  } finally {
    creatingCheckout.value = false
  }
}

async function toggleSuspend(): Promise<void> {
  if (!company.value) return
  mutatingCompany.value = true
  error.value = null
  success.value = null
  try {
    if (company.value.estado === 'activo') {
      await api.post(`/api/v1/global/companies/${company.value.id_empresa}/suspend`)
      success.value = `Empresa ${company.value.nombre} suspendida`
    } else {
      await api.post(`/api/v1/global/companies/${company.value.id_empresa}/activate`)
      success.value = `Empresa ${company.value.nombre} activada`
    }
    await loadData()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo cambiar el estado de la empresa'
  } finally {
    mutatingCompany.value = false
  }
}

async function deleteCompany(): Promise<void> {
  if (!company.value) return
  if (!window.confirm(`¿Eliminar empresa ${company.value.nombre}? Esta acción es irreversible.`)) return
  mutatingCompany.value = true
  error.value = null
  success.value = null
  try {
    await api.delete(`/api/v1/global/companies/${company.value.id_empresa}`)
    await router.push({ name: 'GlobalCompanies' })
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo eliminar la empresa'
  } finally {
    mutatingCompany.value = false
  }
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="space-y-6">
    <section class="rounded-2xl border border-gray-200 bg-white p-5">
      <div class="flex items-center justify-between gap-3">
        <div>
          <h2 class="text-xl font-bold text-gray-900">Gestión de empresa</h2>
          <p class="text-sm text-gray-600 mt-1">Pantalla completa para administrar branding y suscripción.</p>
        </div>
        <Button variant="secondary" @click="router.push({ name: 'GlobalCompanies' })">
          <ArrowLeft :size="14" class="mr-1" /> Volver al listado
        </Button>
      </div>
    </section>

    <p v-if="error" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
    <p v-if="success" class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{{ success }}</p>

    <Card v-if="loading" title="Cargando...">
      <p class="text-sm text-gray-500">Obteniendo información de la empresa.</p>
    </Card>

    <template v-else-if="company">
      <Card title="Acciones rápidas" subtitle="Gestión con botones directos">
        <div class="flex flex-wrap gap-2">
          <Button :loading="savingCompany" @click="saveCompany">
            <Save :size="14" class="mr-1" /> Guardar datos
          </Button>
          <Button :loading="savingSubscription" variant="secondary" @click="saveSubscription">
            <CreditCard :size="14" class="mr-1" /> Guardar suscripción
          </Button>
          <Button :loading="creatingCheckout" variant="secondary" @click="createCheckout">
            <Receipt :size="14" class="mr-1" /> Generar checkout
          </Button>
          <Button :loading="mutatingCompany" variant="secondary" @click="toggleSuspend">
            <component :is="company.estado === 'activo' ? EyeOff : Eye" :size="14" class="mr-1" />
            {{ company.estado === 'activo' ? 'Suspender empresa' : 'Activar empresa' }}
          </Button>
          <Button :loading="mutatingCompany" variant="danger" @click="deleteCompany">
            <Trash2 :size="14" class="mr-1" /> Eliminar empresa
          </Button>
        </div>
      </Card>

      <Card title="Datos de empresa" subtitle="Información legal y branding ERP">
        <form class="space-y-4" @submit.prevent="saveCompany">
          <div class="flex items-center gap-3 p-3 rounded-lg border bg-gray-50">
            <div class="h-12 w-12 rounded-lg border bg-white overflow-hidden flex items-center justify-center">
              <img
                v-if="companyForm.branding_logo_url"
                :src="companyForm.branding_logo_url"
                :alt="companyForm.nombre ?? company.nombre"
                class="h-full w-full object-cover"
              />
              <Building2 v-else :size="20" class="text-gray-400" />
            </div>
            <div>
              <p class="text-sm text-gray-500">Vista previa</p>
              <p class="font-semibold text-gray-900">{{ companyForm.branding_nombre || companyForm.nombre || company.nombre }}</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Nombre legal</label>
              <input v-model="companyForm.nombre" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" required />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">RUC</label>
              <input v-model="companyForm.ruc" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" required />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Branding ERP</label>
              <input v-model="companyForm.branding_nombre" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" placeholder="Opcional" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Logo URL</label>
              <input v-model="companyForm.branding_logo_url" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" placeholder="https://..." />
            </div>
          </div>

          <div class="flex flex-wrap gap-2">
            <Button :loading="savingCompany" type="submit">
              <Save :size="14" class="mr-1" /> Guardar datos
            </Button>
            <Button :loading="mutatingCompany" type="button" variant="secondary" @click="toggleSuspend">
              <component :is="company.estado === 'activo' ? EyeOff : Eye" :size="14" class="mr-1" />
              {{ company.estado === 'activo' ? 'Suspender empresa' : 'Activar empresa' }}
            </Button>
            <Button :loading="mutatingCompany" type="button" variant="danger" @click="deleteCompany">
              <Trash2 :size="14" class="mr-1" /> Eliminar empresa
            </Button>
          </div>
        </form>
      </Card>

      <Card title="Suscripción" subtitle="Plan, ciclo, estado y checkout">
        <div class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Plan</label>
              <select v-model="subscriptionForm.plan_tier" class="w-full rounded-lg border px-3 py-2 text-sm">
                <option v-for="plan in plans" :key="plan.plan" :value="plan.plan">{{ plan.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Ciclo</label>
              <select v-model="subscriptionForm.billing_cycle" class="w-full rounded-lg border px-3 py-2 text-sm">
                <option value="monthly">Mensual</option>
                <option value="yearly">Anual</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Estado</label>
              <select v-model="subscriptionForm.status" class="w-full rounded-lg border px-3 py-2 text-sm">
                <option value="active">Activa</option>
                <option value="trial">Trial</option>
                <option value="past_due">Past due</option>
                <option value="canceled">Cancelada</option>
                <option value="pending">Pendiente</option>
              </select>
            </div>
          </div>

          <div class="flex flex-wrap gap-2">
            <Button
              v-for="preset in plans.filter((item) => item.plan !== 'custom')"
              :key="`preset-${preset.plan}`"
              size="sm"
              variant="secondary"
              type="button"
              @click="applyPlanPreset(preset.plan)"
            >
              Preset {{ preset.name }}
            </Button>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Features (separadas por coma)</label>
            <input v-model="subscriptionForm.feature_overrides" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" placeholder="E1, E2, limit_total_users:10" />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Notas</label>
            <textarea v-model="subscriptionForm.custom_notes" rows="2" class="w-full rounded-lg border px-3 py-2 text-sm" />
          </div>

          <div class="flex flex-wrap gap-2">
            <Button :loading="savingSubscription" @click="saveSubscription">
              <CreditCard :size="14" class="mr-1" /> Guardar suscripción
            </Button>
            <Button :loading="creatingCheckout" variant="secondary" @click="createCheckout">
              <Receipt :size="14" class="mr-1" /> Generar checkout
            </Button>
          </div>
        </div>
      </Card>
    </template>
  </div>
</template>

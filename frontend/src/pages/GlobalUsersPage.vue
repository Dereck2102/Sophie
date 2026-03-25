<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Card from '../components/ui/Card.vue'
import Button from '../components/ui/Button.vue'
import api from '../services/api'
import type { GlobalCompanyUser, GlobalUserPasswordResetOut, PlanPreset, SubscriptionPlanTier, SubscriptionStatus, BillingCycle, UserSubscription } from '../types'

const loading = ref(false)
const mutating = ref(false)
const savingSubscription = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)

const users = ref<GlobalCompanyUser[]>([])
const userSubscriptions = ref<UserSubscription[]>([])
const plans = ref<PlanPreset[]>([])
const selectedUserId = ref<number | null>(null)

const subForm = ref<{
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

const selectedUser = computed(() => users.value.find((item) => item.id_usuario === selectedUserId.value) ?? null)

function parseFeatureOverrides(raw: string): string[] {
  return raw
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
}

function selectUser(userId: number): void {
  selectedUserId.value = userId
  const current = userSubscriptions.value.find((item) => item.id_usuario === userId)
  if (!current) {
    subForm.value = {
      plan_tier: 'starter',
      billing_cycle: 'monthly',
      status: 'pending',
      custom_notes: '',
      feature_overrides: '',
    }
    return
  }

  subForm.value = {
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
  subForm.value.plan_tier = plan
  subForm.value.feature_overrides = preset.features.join(', ')
}

async function loadUsers(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const [usersRes, subsRes, plansRes] = await Promise.all([
      api.get<GlobalCompanyUser[]>('/api/v1/global/users', { params: { limit: 1500 } }),
      api.get<UserSubscription[]>('/api/v1/admin/subscriptions/users', { params: { limit: 1500 } }),
      api.get<PlanPreset[]>('/api/v1/subscriptions/plans'),
    ])
    users.value = usersRes.data
    userSubscriptions.value = subsRes.data
    plans.value = plansRes.data

    if (!selectedUserId.value && users.value.length > 0 && users.value[0]) {
      selectUser(users.value[0].id_usuario)
    } else if (selectedUserId.value) {
      selectUser(selectedUserId.value)
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo cargar usuarios globales'
  } finally {
    loading.value = false
  }
}

async function saveUserSubscription(): Promise<void> {
  if (!selectedUserId.value) return
  savingSubscription.value = true
  error.value = null
  success.value = null
  try {
    await api.put(`/api/v1/admin/subscriptions/users/${selectedUserId.value}`, {
      plan_tier: subForm.value.plan_tier,
      billing_cycle: subForm.value.billing_cycle,
      status: subForm.value.status,
      custom_notes: subForm.value.custom_notes || null,
      feature_overrides: parseFeatureOverrides(subForm.value.feature_overrides),
    })
    success.value = 'Suscripción individual actualizada'
    await loadUsers()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo actualizar la suscripción individual'
  } finally {
    savingSubscription.value = false
  }
}

async function createUserCheckout(): Promise<void> {
  if (!selectedUserId.value) return
  mutating.value = true
  error.value = null
  success.value = null
  try {
    const { data } = await api.post<{ id_pago: number; detail: string; checkout_url?: string | null }>('/api/v1/subscriptions/checkout', {
      plan: subForm.value.plan_tier,
      billing_cycle: subForm.value.billing_cycle,
      id_usuario_owner: selectedUserId.value,
      custom_requirements: subForm.value.plan_tier === 'custom' ? subForm.value.custom_notes : undefined,
    })
    success.value = `${data.detail} #${data.id_pago}`
    if (data.checkout_url) {
      window.open(data.checkout_url, '_blank', 'noopener,noreferrer')
    }
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo generar checkout individual'
  } finally {
    mutating.value = false
  }
}

async function toggleUser(user: GlobalCompanyUser): Promise<void> {
  mutating.value = true
  error.value = null
  success.value = null
  try {
    await api.patch(`/api/v1/global/users/${user.id_usuario}/activation`, { activo: !user.activo })
    success.value = `Usuario ${user.username} ${user.activo ? 'desactivado' : 'activado'}`
    await loadUsers()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo cambiar el estado del usuario'
  } finally {
    mutating.value = false
  }
}

async function forceReset(user: GlobalCompanyUser): Promise<void> {
  mutating.value = true
  error.value = null
  success.value = null
  try {
    const { data } = await api.post<GlobalUserPasswordResetOut>(`/api/v1/global/users/${user.id_usuario}/force-password-reset`)
    success.value = `Token temporal para ${user.username}: ${data.reset_token}`
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? 'No se pudo forzar el reseteo de contraseña'
  } finally {
    mutating.value = false
  }
}

onMounted(() => {
  void loadUsers()
})
</script>

<template>
  <div class="space-y-6">
    <section class="rounded-2xl border border-gray-200 bg-white p-5">
      <h2 class="text-xl font-bold text-gray-900">Gestión Global de Usuarios</h2>
      <p class="text-sm text-gray-600 mt-1">Selecciona un usuario para asignar su plan individual sin vincularlo al plan empresarial.</p>
    </section>

    <p v-if="error" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
    <p v-if="success" class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 break-all">{{ success }}</p>

    <Card title="Usuarios maestros" subtitle="SOPHIE ADMIN · Superadmin">
      <div v-if="loading" class="text-sm text-gray-500">Cargando usuarios...</div>
      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left border-b border-gray-200">
              <th class="px-2 py-2">Usuario</th>
              <th class="px-2 py-2">Email</th>
              <th class="px-2 py-2">Empresa</th>
              <th class="px-2 py-2">Rol Maestro</th>
              <th class="px-2 py-2">Estado</th>
              <th class="px-2 py-2">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in users"
              :key="item.id_usuario"
              class="border-b border-gray-100 cursor-pointer"
              :class="selectedUserId === item.id_usuario ? 'bg-blue-50' : ''"
              @click="selectUser(item.id_usuario)"
            >
              <td class="px-2 py-2 font-medium">{{ item.username }}</td>
              <td class="px-2 py-2">{{ item.email }}</td>
              <td class="px-2 py-2">{{ item.empresa_nombre ?? 'Global' }}</td>
              <td class="px-2 py-2 uppercase">{{ item.rol_fijo }}</td>
              <td class="px-2 py-2">
                <span :class="item.activo ? 'text-emerald-700' : 'text-amber-700'">{{ item.activo ? 'Activo' : 'Inactivo' }}</span>
              </td>
              <td class="px-2 py-2">
                <div class="flex flex-wrap gap-2" @click.stop>
                  <Button size="sm" variant="secondary" :disabled="mutating" @click="toggleUser(item)">
                    {{ item.activo ? 'Desactivar' : 'Activar' }}
                  </Button>
                  <Button size="sm" variant="secondary" :disabled="mutating" @click="forceReset(item)">Forzar reset</Button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>

    <Card title="Suscripción individual" subtitle="Plan independiente del plan empresarial">
      <div v-if="!selectedUser" class="text-sm text-gray-500">Selecciona un usuario de la tabla.</div>
      <div v-else class="space-y-4">
        <div class="text-sm text-gray-600">
          Usuario seleccionado: <span class="font-semibold text-gray-900">{{ selectedUser.username }}</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Plan</label>
            <select v-model="subForm.plan_tier" class="w-full rounded-lg border px-3 py-2 text-sm">
              <option v-for="plan in plans" :key="plan.plan" :value="plan.plan">{{ plan.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Ciclo</label>
            <select v-model="subForm.billing_cycle" class="w-full rounded-lg border px-3 py-2 text-sm">
              <option value="monthly">Mensual</option>
              <option value="yearly">Anual</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Estado</label>
            <select v-model="subForm.status" class="w-full rounded-lg border px-3 py-2 text-sm">
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
            :key="`user-preset-${preset.plan}`"
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
          <input v-model="subForm.feature_overrides" type="text" class="w-full rounded-lg border px-3 py-2 text-sm" placeholder="E1, E2, limit_total_users:5" />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Notas</label>
          <textarea v-model="subForm.custom_notes" rows="2" class="w-full rounded-lg border px-3 py-2 text-sm" />
        </div>

        <div class="flex flex-wrap gap-2">
          <Button :loading="savingSubscription" @click="saveUserSubscription">Guardar suscripción individual</Button>
          <Button :loading="mutating" variant="secondary" @click="createUserCheckout">Generar checkout individual</Button>
        </div>
      </div>
    </Card>
  </div>
</template>

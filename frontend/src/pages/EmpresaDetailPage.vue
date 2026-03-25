<template>
  <div class="empresa-detail-container">
    <!-- Header de Empresa -->
    <header class="empresa-header border-b">
      <div class="empresa-header-content flex items-center justify-between p-4">
        <div class="empresa-info flex items-center gap-4">
          <img
            v-if="empresa?.branding_logo_url"
            :src="empresa.branding_logo_url"
            :alt="empresa.razon_social"
            class="empresa-logo w-12 h-12 rounded"
          />
          <div class="empresa-text">
            <h1 class="text-2xl font-bold">{{empresa?.branding_nombre || empresa?.razon_social}}</h1>
            <p class="text-sm text-gray-600">RUC: {{empresa?.ruc}}</p>
            <p v-if="empresa?.branding_slogan" class="text-sm text-gray-500 italic">{{empresa.branding_slogan}}</p>
          </div>
        </div>
        <div class="empresa-status">
          <Badge :variant="subscriptionStatusVariant">{{suscripcionStatus}}</Badge>
        </div>
      </div>

      <!-- Sub-navegación de Empresa -->
      <nav class="empresa-nav border-t flex gap-6 px-4 overflow-x-auto">
        <router-link
          :to="{ name: 'EmpresaDashboard', params: { empresaId } }"
          active-class="active border-b-2 border-primary text-primary"
          class="nav-item py-4 px-2 text-sm font-medium hover:text-primary transition"
        >
          📊 Dashboard
        </router-link>

        <router-link
          v-if="canManageUsers"
          :to="{ name: 'EmpresaUsuarios', params: { empresaId } }"
          active-class="active border-b-2 border-primary text-primary"
          class="nav-item py-4 px-2 text-sm font-medium hover:text-primary transition"
        >
          👥 Usuarios
        </router-link>

        <router-link
          v-if="canConfigure"
          :to="{ name: 'EmpresaConfiguracion', params: { empresaId } }"
          active-class="active border-b-2 border-primary text-primary"
          class="nav-item py-4 px-2 text-sm font-medium hover:text-primary transition"
        >
          ⚙️ Configuración
        </router-link>

        <router-link
          v-if="hasModule('E4')"
          :to="{ name: 'EmpresaVentas', params: { empresaId } }"
          active-class="active border-b-2 border-primary text-primary"
          class="nav-item py-4 px-2 text-sm font-medium hover:text-primary transition"
        >
          💰 Ventas
        </router-link>

        <router-link
          v-if="hasModule('E8')"
          :to="{ name: 'EmpresaTaller', params: { empresaId } }"
          active-class="active border-b-2 border-primary text-primary"
          class="nav-item py-4 px-2 text-sm font-medium hover:text-primary transition"
        >
          🔧 Taller
        </router-link>

        <router-link
          v-if="hasModule('E6')"
          :to="{ name: 'EmpresaProyectos', params: { empresaId } }"
          active-class="active border-b-2 border-primary text-primary"
          class="nav-item py-4 px-2 text-sm font-medium hover:text-primary transition"
        >
          📋 Proyectos
        </router-link>

        <router-link
          v-if="hasModule('E5')"
          :to="{ name: 'EmpresaCompras', params: { empresaId } }"
          active-class="active border-b-2 border-primary text-primary"
          class="nav-item py-4 px-2 text-sm font-medium hover:text-primary transition"
        >
          🛒 Compras
        </router-link>

        <router-link
          v-if="hasModule('E3')"
          :to="{ name: 'EmpresaCajaChica', params: { empresaId } }"
          active-class="active border-b-2 border-primary text-primary"
          class="nav-item py-4 px-2 text-sm font-medium hover:text-primary transition"
        >
          💵 Caja Chica
        </router-link>

        <router-link
          v-if="hasModule('E2')"
          :to="{ name: 'EmpresaAuditoria', params: { empresaId } }"
          active-class="active border-b-2 border-primary text-primary"
          class="nav-item py-4 px-2 text-sm font-medium hover:text-primary transition"
        >
          📝 Auditoría
        </router-link>
      </nav>
    </header>

    <!-- Contenido anidado -->
    <main class="empresa-content p-6">
      <router-view></router-view>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useClienteStore } from '../stores/clientes'
import { useSubscriptionStore } from '../stores/subscription'
import { useAuthStore } from '../stores/auth'
import Badge from '../components/ui/Badge.vue'
import type { Empresa, Cliente, EmpresaSubscription } from '../types'

const route = useRoute()
const clienteStore = useClienteStore()
const subscriptionStore = useSubscriptionStore()
const authStore = useAuthStore()

const empresaId = computed(() => parseInt(route.params.empresaId as string))

const empresa = computed(() => {
  return (clienteStore.clientes as Cliente[]).find(c => c.id_cliente === empresaId.value)?.empresa as Empresa | undefined
})

const suscripcion = computed(() => {
  // Obtener suscripción actual del store
  return subscriptionStore.current as EmpresaSubscription | null
})

const suscripcionStatus = computed(() => {
  if (!suscripcion.value) return 'Sin información'
  const status = suscripcion.value.status
  const statusLabels: Record<string, string> = {
    'active': 'Activa',
    'trial': 'Prueba',
    'past_due': 'Vencido',
    'canceled': 'Cancelada',
    'pending': 'Pendiente',
  }
  return statusLabels[status] || status
})

const subscriptionStatusVariant = computed(() => {
  const status = suscripcion.value?.status
  switch (status) {
    case 'active':
      return 'success'
    case 'trial':
      return 'warning'
    case 'past_due':
      return 'danger'
    case 'canceled':
      return 'default'
    default:
      return 'default'
  }
})

const canManageUsers = computed(() => {
  return authStore.user?.rol === 'admin' || authStore.user?.rol === 'superadmin'
})

const canConfigure = computed(() => {
  return authStore.user?.rol === 'admin' || authStore.user?.rol === 'superadmin'
})

const hasModule = (moduleCode: string): boolean => {
  return subscriptionStore.hasModule(moduleCode as any)
}

// Validar que el usuario pertenece a esta empresa
if (authStore.user?.id_empresa !== empresaId.value && authStore.user?.rol !== 'superadmin') {
  // Redirect a empresas si no tiene acceso
  location.href = '/empresas'
}
</script>

<style scoped>
.empresa-detail-container {
  min-height: 100vh;
  background-color: #f9fafb;
}

.empresa-header {
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.empresa-header-content {
  max-width: 100%;
}

.empresa-logo {
  object-fit: cover;
  border: 1px solid #e5e7eb;
}

.empresa-nav {
  background: white;
}

.nav-item {
  border-bottom: 2px solid transparent;
  color: #6b7280;
  transition: all 0.2s ease;
}

.nav-item:hover {
  color: #3b82f6;
  border-bottom-color: #dbeafe;
}

.nav-item.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
}
</style>

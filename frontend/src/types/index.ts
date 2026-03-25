// API Types for SOPHIE ERP/CRM

export type RolEnum =
  | 'superadmin'
  | 'admin'
  | 'agente_soporte'
  | 'ventas'
  | 'contable'
  | 'rrhh'
  | 'bodega'
  | 'jefe_tecnologias'
  | 'jefe_taller'
  | 'jefe_administrativo'
  | 'jefe_contable'
  | 'ejecutivo'
  | 'administrativo_contable'
  | 'tecnico'
  | 'tecnico_taller'
  | 'agente_soporte_l1'
  | 'agente_soporte_l2'
  | 'desarrollador'

export type TipoCliente = 'B2B' | 'B2C'
export type EstadoCliente = 'activo' | 'inactivo' | 'prospecto'
export type TipoSuscripcion = 'individual' | 'corporativa'
export type EstadoCotizacion = 'borrador' | 'enviada' | 'aprobada' | 'rechazada' | 'facturada'
export type EstadoVenta = 'pendiente' | 'procesando' | 'facturada' | 'anulada'
export type EstadoTicket = 'abierto' | 'en_progreso' | 'esperando_cliente' | 'resuelto' | 'cerrado'
export type TipoTicket = 'reparacion' | 'incidencia_it'
export type PrioridadTicket = 'baja' | 'media' | 'alta' | 'critica'
export type EstadoSerie = 'disponible' | 'vendido' | 'en_reparacion' | 'baja'
export type EstadoProyecto = 'propuesta' | 'en_progreso' | 'pausado' | 'completado' | 'cancelado'
export type EstadoTarea = 'pendiente' | 'en_progreso' | 'completado'
export type SubscriptionPlanTier = 'starter' | 'pro' | 'enterprise' | 'custom'
export type BillingCycle = 'monthly' | 'yearly'
export type SubscriptionStatus = 'active' | 'trial' | 'past_due' | 'canceled' | 'pending'
export type PaymentStatus = 'pending' | 'paid' | 'failed' | 'canceled'
export type PaymentGatewayProvider = 'payphone' | 'stripe'

export interface Usuario {
  id_usuario: number
  username: string
  email: string
  rol: RolEnum
  nombre_completo?: string
  telefono_recuperacion?: string
  activo: boolean
  mfa_habilitado: boolean
  force_mfa: boolean
  foto_perfil_url?: string
  email_verificado: boolean
  telefono_verificado: boolean
  permisos: string[]
  vistas: string[]
  herramientas: string[]
  fecha_creacion: string
  // Nuevos campos para suscripción dual
  tipo_suscripcion: TipoSuscripcion
  id_cliente: number
  id_empresa?: number
  es_admin_global: boolean
}

export interface RoleAccessProfile {
  permisos: string[]
  vistas: string[]
  herramientas: string[]
}

export type RoleProfilesResponse = Record<RolEnum, RoleAccessProfile>

export interface TenantStaffingBucket {
  key: string
  label: string
  limit?: number | null
  used: number
  remaining?: number | null
}

export interface TenantStaffingLimits {
  id_cliente: number
  plan_tier: string
  total_limit?: number | null
  total_used: number
  total_remaining?: number | null
  by_role: TenantStaffingBucket[]
  by_area: TenantStaffingBucket[]
}

export interface ConfiguracionSistema {
  nombre_instancia: string
  nombre_empresa: string
  ruc_empresa?: string
  logo_empresa_url?: string
  timezone: string
  market: string
  email_notifications: boolean
  system_notifications: boolean
  session_timeout_minutes: number
  require_mfa_global: boolean
  auth_twofa_enabled: boolean
  auth_channel_email_enabled: boolean
  auth_channel_sms_enabled: boolean
  auth_channel_app_enabled: boolean
  max_login_attempts: number
  color_primario?: string
  color_secundario?: string
  reporte_footer?: string
  iva_default_percent: number
  descuento_default_percent: number
  costo_hora_tecnica_default: number
  costo_movilizacion_default: number
  costo_software_default: number
  costo_material_default: number
  costo_mano_obra_default: number
  fondo_caja_chica_mensual: number
}

// Nuevas configuraciones para arquitectura dual B2B/B2C
export interface ConfiguracionEmpresa {
  id_config?: number
  id_cliente: number
  timezone: string
  market: string
  require_mfa_global: boolean
  session_timeout_minutes: number
  max_login_attempts: number
  color_primario?: string
  color_secundario?: string
  default_iva: number
  default_descuento: number
  payphone_key?: string
  payphone_secret?: string
  stripe_key?: string
  fecha_creacion?: string
  fecha_actualizacion?: string
}

export interface ConfiguracionUsuario {
  id_config?: number
  id_usuario: number
  preferencia_idioma: 'es' | 'en'
  tema: 'light' | 'dark' | 'system'
  notificaciones_email: boolean
  notificaciones_sms: boolean
  timezone_personal?: string
  reporte_footer?: string
  fecha_actualizacion?: string
}

export interface SuscripcionDetalle {
  id_suscripcion?: number
  id_cliente: number
  tipo: TipoSuscripcion
  plan_tier: SubscriptionPlanTier
  billing_cycle: BillingCycle
  status: SubscriptionStatus
  fecha_inicio: string
  fecha_fin?: string
  price_usd: number
  modules_enabled?: string[]
  seat_limit?: number
  features_individual?: {
    has_advanced_reporting: boolean
    has_custom_branding: boolean
    max_storage_gb: number
  }
}

export interface AuditoriaLog {
  id_log: number
  id_cliente?: number
  empresa_nombre?: string
  id_usuario?: number
  usuario_username?: string
  usuario_nombre?: string
  accion: string
  accion_tipo?: string
  accion_nombre?: string
  modulo: string
  metodo_http?: string
  ruta?: string
  ip_origen?: string
  user_agent?: string
  pais_origen?: string
  ciudad_origen?: string
  ubicacion_aprox?: string
  detalle?: Record<string, unknown>
  fecha: string
}

export interface BackupUsuarioItem {
  username: string
  email: string
  password_hash: string
  rol: RolEnum
  nombre_completo?: string
  activo: boolean
  mfa_habilitado: boolean
  force_mfa: boolean
  foto_perfil_url?: string
  email_verificado: boolean
  permisos: string[]
  vistas: string[]
  herramientas: string[]
}

export interface BackupUsuariosPayload {
  generated_at: string
  settings?: ConfiguracionSistema
  users: BackupUsuarioItem[]
}

export interface AuthChannelsStatus {
  twofa_env_enabled: boolean
  twofa_enabled: boolean
  channel_email_enabled: boolean
  channel_sms_enabled: boolean
  channel_app_enabled: boolean
  smtp_configured: boolean
  twilio_configured: boolean
  email_effective: boolean
  sms_effective: boolean
  app_effective: boolean
}

export interface PlanPreset {
  plan: SubscriptionPlanTier
  name: string
  description: string
  monthly_price_usd?: number | null
  yearly_price_usd?: number | null
  features: string[]
}

export interface EmpresaSubscription {
  id_empresa: number
  empresa_nombre: string
  plan_tier: SubscriptionPlanTier
  billing_cycle: BillingCycle
  status: SubscriptionStatus
  price_usd: number
  currency: string
  features: string[]
  custom_notes?: string | null
  updated_by_user_id?: number | null
  updated_at?: string | null
}

export interface CheckoutResponse {
  id_pago: number
  provider: string
  status: PaymentStatus
  amount: number
  currency: string
  checkout_url?: string | null
  detail: string
}

export interface CustomOrderResponse {
  id_pago: number
  order_number: string
  status: PaymentStatus
  amount: number
  currency: string
  checkout_url?: string | null
  detail: string
}

export interface PendingCustomOrder {
  id_order: number
  order_number: string
  id_pago?: number | null
  id_empresa: number
  empresa_nombre: string
  billing_cycle: BillingCycle
  amount: number
  currency: string
  status: 'pending' | 'approved' | 'activated' | 'canceled'
  created_at: string
}

export interface PaymentGatewayConfig {
  provider: PaymentGatewayProvider
  enabled: boolean
  public_key?: string | null
  has_secret: boolean
  endpoint_url?: string | null
  store_id?: string | null
  return_url?: string | null
  cancel_url?: string | null
  has_webhook_token?: boolean
  updated_by_user_id?: number | null
  updated_at?: string | null
}

export interface PublicPlan {
  key: string
  name: string
  tier: SubscriptionPlanTier
  description: string
  monthly_price_usd?: number | null
  yearly_price_usd?: number | null
  modules: string[]
}

export interface PlatformLayer {
  key: 'public' | 'global' | 'enterprise'
  name: string
  description: string
}

export interface PublicLanding {
  platform_name: string
  platform_version: string
  layers: PlatformLayer[]
  plans: PublicPlan[]
}

export interface GlobalPlanCount {
  tier: SubscriptionPlanTier
  companies: number
}

export interface GlobalDashboardSummary {
  total_companies: number
  active_companies: number
  suspended_or_inactive_companies: number
  registered_users: number
  active_subscriptions: number
  pending_subscriptions: number
  paid_transactions: number
  mrr_usd: number
  plan_breakdown: GlobalPlanCount[]
  system_status: string
}

export interface GlobalCompany {
  id_empresa: number
  nombre: string
  branding_nombre?: string | null
  branding_logo_url?: string | null
  ruc: string
  estado: EstadoCliente
  plan_tier: SubscriptionPlanTier
  billing_cycle: BillingCycle
  subscription_status: SubscriptionStatus
  modules_enabled: string[]
  fecha_inicio: string
  price_usd: number
  currency: string
}

export interface GlobalCompanyUpdate {
  nombre?: string
  branding_nombre?: string
  branding_logo_url?: string
  ruc?: string
  contacto_principal?: string
  telefono?: string
  email?: string
  direccion?: string
  sector?: string
}

export interface GlobalCompanyUser {
  id_usuario: number
  username: string
  email: string
  rol: RolEnum
  rol_fijo: 'superadmin' | 'admin'
  activo: boolean
  id_empresa?: number | null
  empresa_nombre?: string | null
}

export interface UserSubscription {
  id_usuario: number
  username: string
  email: string
  plan_tier: SubscriptionPlanTier
  billing_cycle: BillingCycle
  status: SubscriptionStatus
  price_usd: number
  currency: string
  features: string[]
  custom_notes?: string | null
  updated_by_user_id?: number | null
  updated_at?: string | null
}

export interface GlobalUserActivationIn {
  activo: boolean
}

export interface GlobalUserPasswordResetOut {
  id_usuario: number
  reset_token: string
  expires_at: string
}

export interface EmailVerificationTokenResponse {
  token: string
  expires_at: string
}

export interface Empresa {
  id_cliente: number
  razon_social: string
  ruc: string
  contacto_principal?: string
  telefono?: string
  email?: string
  direccion?: string
  sector?: string
  branding_nombre?: string
  branding_logo_url?: string
  branding_slogan?: string
  configuracion?: ConfiguracionEmpresa
}

export interface ClienteB2C {
  id_cliente: number
  nombre_completo: string
  documento_identidad: string
  telefono?: string
  email?: string
  direccion?: string
}

export interface Cliente {
  id_cliente: number
  tipo_cliente: TipoCliente
  fecha_registro: string
  estado: EstadoCliente
  empresa?: Empresa
  cliente_b2c?: ClienteB2C
}

export interface DetalleCotizacion {
  id_detalle: number
  id_producto: number
  cantidad: number
  precio_unitario: number
  descuento: number
  subtotal: number
  costo_material_unitario?: number
  costo_material_total?: number
  margen_unitario?: number
  margen_total?: number
  rentabilidad_pct?: number
}

export interface Cotizacion {
  id_cotizacion: number
  numero: string
  id_cliente: number
  id_vendedor: number
  id_proyecto?: number
  estado: EstadoCotizacion
  subtotal: number
  impuesto: number
  total: number
  costo_mano_obra?: number
  costo_movilizacion?: number
  costo_software?: number
  horas_soporte?: number
  tarifa_hora_soporte?: number
  costo_servicios_total?: number
  notas?: string
  fecha_creacion: string
  fecha_vencimiento?: string
  costo_materiales_total?: number
  margen_bruto_total?: number
  utilidad_neta_operativa?: number
  rentabilidad_pct?: number
  detalles: DetalleCotizacion[]
}

export type TipoMovimientoCaja = 'ingreso' | 'egreso' | 'ajuste'

export interface MovimientoCajaChica {
  id_movimiento: number
  tipo: TipoMovimientoCaja
  concepto: string
  categoria?: string
  monto: number
  responsable?: string
  observacion?: string
  fecha: string
}

export interface CajaChicaResumen {
  balance_actual: number
  ingresos_mes: number
  egresos_mes: number
  movimientos_mes: number
  fondo_mensual: number
  disponible_mes: number
}

export interface Ticket {
  id_ticket: number
  numero: string
  tipo: TipoTicket
  id_cliente: number
  id_proyecto?: number
  id_tecnico?: number
  prioridad: PrioridadTicket
  estado: EstadoTicket
  titulo: string
  descripcion?: string
  fecha_creacion: string
  fecha_inicio_trabajo?: string
  fecha_fin_trabajo?: string
  fecha_cierre?: string
}

export interface Inventario {
  id_producto: number
  codigo: string
  nombre: string
  descripcion?: string
  categoria: string
  requiere_serie: boolean
  stock_actual: number
  stock_minimo: number
  precio_venta: number
  costo_adquisicion: number
  id_proveedor?: number
}

export interface InventarioSerie {
  id_serie: number
  id_producto: number
  numero_serie: string
  estado: EstadoSerie
  fecha_ingreso: string
}

export interface EventoCliente {
  id_evento: number
  tipo_evento: string
  descripcion: string
  fecha: string
}

export interface Tarea {
  id_tarea: number
  id_proyecto: number
  titulo: string
  descripcion?: string
  estado: EstadoTarea
  prioridad: string
  id_asignado?: number
  fecha_vencimiento?: string
  etiquetas?: string
  horas_estimadas?: number
  horas_reales: number
  fecha_creacion: string
}

export interface Proyecto {
  id_proyecto: number
  id_cliente: number
  nombre: string
  descripcion?: string
  estado: EstadoProyecto
  presupuesto?: number
  fecha_inicio?: string
  fecha_fin?: string
  fecha_creacion: string
}

export interface ProyectoRentabilidad {
  id_proyecto: number
  presupuesto: number
  ingresos_facturados: number
  costo_horas_tecnicas: number
  costo_reparaciones: number
  costo_repuestos: number
  costo_total_operativo: number
  margen_presupuestario: number
  utilidad_neta_real: number
  margen_neto_pct: number
  consumo_presupuesto_pct: number
  tickets_total: number
  tickets_cerrados: number
}

export interface ProyectoEstadisticas {
  id_proyecto: number
  nombre: string
  estado: EstadoProyecto
  total_tareas: number
  tareas_completadas: number
  tareas_pendientes: number
  tareas_en_progreso: number
  porcentaje_completacion: number
  tickets_asociados: number
  horas_estimadas: number
  horas_realizadas: number
  variancia_horas_pct: number
  miembros_asignados: number
  presupuesto?: number
  ingresos_facturados: number
  margen_neto_pct: number
  fecha_inicio?: string
  fecha_fin?: string
  dias_restantes?: number
}

export interface CotizacionProyectoResumen {
  id_cotizacion: number
  numero: string
  estado: string
  total: number
  fecha_creacion: string
  numero_factura?: string
  fecha_factura?: string
}

export interface RepuestoUsado {
  id_repuesto: number
  id_producto: number
  id_serie?: number
  cantidad: number
  precio_unitario: number
}

export interface Reparacion {
  id_ticket: number
  equipo_descripcion?: string
  marca_equipo?: string
  modelo_equipo?: string
  numero_serie_equipo?: string
  accesorios_recibidos?: string
  diagnostico?: string
  fotos_urls?: string
  costo_reparacion?: number
  token_seguimiento?: string
  email_cliente?: string
  repuestos: RepuestoUsado[]
}

export interface OrdenTrabajoPublic {
  ticket_numero: string
  ticket_titulo: string
  ticket_descripcion?: string
  ticket_estado: string
  ticket_prioridad: string
  ticket_fecha_creacion: string
  ticket_fecha_inicio?: string
  ticket_fecha_fin?: string
  equipo_descripcion?: string
  marca_equipo?: string
  modelo_equipo?: string
  numero_serie_equipo?: string
  accesorios_recibidos?: string
  diagnostico?: string
  costo_reparacion?: number
  repuestos: RepuestoUsado[]
}

export interface TokenResponse {
  access_token: string
  token_type: string
  mfa_required: boolean
  session_id?: string
  access_expires_in?: number
  mfa_channel?: string
  mfa_destination?: string
  mfa_phone_destination?: string
  mfa_debug_code?: string
}

export interface LoginRequest {
  username: string
  password: string
  mfa_code?: string
  recovery_code?: string
}

export interface PasswordRecoveryRequest {
  identifier: string
}

export interface PasswordRecoveryConfirmRequest {
  token: string
  new_password: string
}

export interface RecoveryCodesResponse {
  codes: string[]
  generated_at: string
}

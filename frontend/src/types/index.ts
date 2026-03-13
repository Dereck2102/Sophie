// API Types for SOPHIE ERP/CRM

export type RolEnum = 'superadmin' | 'ejecutivo' | 'administrativo_contable' | 'tecnico'

export type TipoCliente = 'B2B' | 'B2C'
export type EstadoCliente = 'activo' | 'inactivo' | 'prospecto'
export type EstadoCotizacion = 'borrador' | 'enviada' | 'aprobada' | 'rechazada' | 'facturada'
export type EstadoVenta = 'pendiente' | 'procesando' | 'facturada' | 'anulada'
export type EstadoTicket = 'abierto' | 'en_progreso' | 'esperando_cliente' | 'resuelto' | 'cerrado'
export type TipoTicket = 'reparacion' | 'incidencia_it'
export type PrioridadTicket = 'baja' | 'media' | 'alta' | 'critica'
export type EstadoSerie = 'disponible' | 'vendido' | 'en_reparacion' | 'baja'
export type EstadoProyecto = 'propuesta' | 'en_progreso' | 'pausado' | 'completado' | 'cancelado'
export type EstadoTarea = 'pendiente' | 'en_progreso' | 'completado'

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
}

export interface AuditoriaLog {
  id_log: number
  id_usuario?: number
  accion: string
  modulo: string
  ip_origen?: string
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

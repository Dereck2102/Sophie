// API Types for SOPHIE ERP/CRM

export type RolEnum =
  | 'admin'
  | 'vendedor'
  | 'tecnico_taller'
  | 'tecnico_it'
  | 'comprador'
  | 'desarrollador'
  | 'consultor_senior'

export type TipoCliente = 'B2B' | 'B2C'
export type EstadoCliente = 'activo' | 'inactivo' | 'prospecto'
export type EstadoCotizacion = 'borrador' | 'enviada' | 'aprobada' | 'rechazada' | 'facturada'
export type EstadoVenta = 'pendiente' | 'procesando' | 'facturada' | 'anulada'
export type EstadoTicket = 'abierto' | 'en_progreso' | 'esperando_cliente' | 'resuelto' | 'cerrado'
export type TipoTicket = 'reparacion' | 'incidencia_it'
export type PrioridadTicket = 'baja' | 'media' | 'alta' | 'critica'
export type EstadoSerie = 'disponible' | 'vendido' | 'en_reparacion' | 'baja'

export interface Usuario {
  id_usuario: number
  username: string
  email: string
  rol: RolEnum
  nombre_completo?: string
  activo: boolean
  mfa_habilitado: boolean
  fecha_creacion: string
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
}

export interface Cotizacion {
  id_cotizacion: number
  numero: string
  id_cliente: number
  id_vendedor: number
  estado: EstadoCotizacion
  subtotal: number
  impuesto: number
  total: number
  notas?: string
  fecha_creacion: string
  fecha_vencimiento?: string
  detalles: DetalleCotizacion[]
}

export interface Ticket {
  id_ticket: number
  numero: string
  tipo: TipoTicket
  id_cliente: number
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
  id_proveedor?: number
}

export interface EventoCliente {
  id_evento: number
  tipo_evento: string
  descripcion: string
  fecha: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  mfa_required: boolean
}

export interface LoginRequest {
  username: string
  password: string
  mfa_code?: string
}

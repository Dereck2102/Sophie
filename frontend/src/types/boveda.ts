export interface Credencial {
  id_credencial: number
  id_empresa: number
  nombre: string
  usuario_acceso?: string
  url?: string
  notas?: string
}

export interface CredencialReveal extends Credencial {
  password_plain: string
}

export interface CredencialCreatePayload {
  id_empresa: number
  nombre: string
  usuario_acceso?: string
  password_plain: string
  url?: string
  notas?: string
}

export interface CredencialUpdatePayload {
  nombre?: string
  usuario_acceso?: string
  password_plain?: string
  url?: string
  notas?: string
}

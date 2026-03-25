import type { RoleProfilesResponse, RolEnum } from '../types'

export interface AccessOption {
  value: string
  label: string
}

export type AccessArea = 'permisos' | 'vistas' | 'herramientas'

export interface AccessProfile {
  permisos: string[]
  vistas: string[]
  herramientas: string[]
}

export const MASTER_PANEL_ROLES: ReadonlySet<RolEnum> = new Set(['superadmin', 'admin'])

export function isSuperadminRole(role?: RolEnum | null): boolean {
  return role === 'superadmin'
}

export function isMasterPanelRole(role?: RolEnum | null): boolean {
  return Boolean(role && MASTER_PANEL_ROLES.has(role))
}

function resolveProfile(role: RolEnum, roleProfiles: RoleProfilesResponse | null): AccessProfile | null {
  return roleProfiles?.[role] ?? null
}

export function hasRoleProfileAccessWithProfiles(
  role: RolEnum,
  area: AccessArea,
  value: string,
  roleProfiles: RoleProfilesResponse | null
): boolean {
  const profile = resolveProfile(role, roleProfiles)
  if (!profile) return false
  return profile[area].includes('*') || profile[area].includes(value)
}

export function getExpandedRolePreset(
  role: RolEnum,
  options: Record<AccessArea, AccessOption[]>,
  roleProfiles: RoleProfilesResponse | null
): AccessProfile {
  const profile = resolveProfile(role, roleProfiles)
  if (!profile) {
    return {
      permisos: [],
      vistas: [],
      herramientas: [],
    }
  }
  return {
    permisos: profile.permisos.includes('*') ? options.permisos.map((item) => item.value) : [...profile.permisos],
    vistas: profile.vistas.includes('*') ? options.vistas.map((item) => item.value) : [...profile.vistas],
    herramientas: profile.herramientas.includes('*') ? options.herramientas.map((item) => item.value) : [...profile.herramientas],
  }
}
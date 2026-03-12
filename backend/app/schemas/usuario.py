from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.infrastructure.models.usuario import RolEnum


class UsuarioBase(BaseModel):
    username: str
    email: EmailStr
    rol: RolEnum
    nombre_completo: Optional[str] = None


class UsuarioCreate(UsuarioBase):
    password: str
    mfa_habilitado: Optional[bool] = None
    force_mfa: Optional[bool] = None
    permisos: Optional[list[str]] = None
    vistas: Optional[list[str]] = None
    herramientas: Optional[list[str]] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UsuarioUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nombre_completo: Optional[str] = None
    activo: Optional[bool] = None
    rol: Optional[RolEnum] = None
    mfa_habilitado: Optional[bool] = None
    force_mfa: Optional[bool] = None
    permisos: Optional[list[str]] = None
    vistas: Optional[list[str]] = None
    herramientas: Optional[list[str]] = None


class UsuarioSelfUpdate(BaseModel):
    """Schema for users updating their own profile."""
    nombre_completo: Optional[str] = None
    email: Optional[EmailStr] = None
    foto_perfil_url: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if v is not None:
            has_upper = any(ch.isupper() for ch in v)
            has_lower = any(ch.islower() for ch in v)
            has_digit = any(ch.isdigit() for ch in v)
            if not (has_upper and has_lower and has_digit):
                raise ValueError("Password must include uppercase, lowercase, and number")
        return v


class UsuarioOut(UsuarioBase):
    id_usuario: int
    activo: bool
    mfa_habilitado: bool
    force_mfa: bool
    foto_perfil_url: Optional[str] = None
    email_verificado: bool
    permisos: list[str] = []
    vistas: list[str] = []
    herramientas: list[str] = []
    fecha_creacion: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    mfa_required: bool = False


class MFASetupOut(BaseModel):
    secret: str
    uri: str
    qr_image_b64: Optional[str] = None


class MFAVerifyRequest(BaseModel):
    code: str


class RefreshRequest(BaseModel):
    refresh_token: str


class EmailVerificationTokenOut(BaseModel):
    token: str
    expires_at: datetime


class EmailVerificationRequest(BaseModel):
    token: str


class ConfiguracionSistemaOut(BaseModel):
    nombre_instancia: str
    nombre_empresa: str
    ruc_empresa: Optional[str] = None
    logo_empresa_url: Optional[str] = None
    timezone: str
    market: str
    email_notifications: bool
    system_notifications: bool
    session_timeout_minutes: int
    require_mfa_global: bool
    max_login_attempts: int
    color_primario: Optional[str] = None
    color_secundario: Optional[str] = None
    reporte_footer: Optional[str] = None

    model_config = {"from_attributes": True}


class ConfiguracionSistemaUpdate(BaseModel):
    nombre_instancia: Optional[str] = None
    nombre_empresa: Optional[str] = None
    ruc_empresa: Optional[str] = None
    logo_empresa_url: Optional[str] = None
    timezone: Optional[str] = None
    market: Optional[str] = None
    email_notifications: Optional[bool] = None
    system_notifications: Optional[bool] = None
    session_timeout_minutes: Optional[int] = None
    require_mfa_global: Optional[bool] = None
    max_login_attempts: Optional[int] = None
    color_primario: Optional[str] = None
    color_secundario: Optional[str] = None
    reporte_footer: Optional[str] = None


class AuditoriaLogOut(BaseModel):
    id_log: int
    id_usuario: Optional[int] = None
    accion: str
    modulo: str
    ip_origen: Optional[str] = None
    detalle: Optional[dict] = None
    fecha: datetime

    model_config = {"from_attributes": True}


class BackupUsuariosOut(BaseModel):
    generated_at: datetime
    settings: Optional[ConfiguracionSistemaOut] = None
    users: list["BackupUsuarioItemOut"]


class BackupUsuarioItemOut(BaseModel):
    username: str
    email: EmailStr
    password_hash: str
    rol: RolEnum
    nombre_completo: Optional[str] = None
    activo: bool
    mfa_habilitado: bool
    force_mfa: bool
    foto_perfil_url: Optional[str] = None
    email_verificado: bool
    permisos: list[str] = []
    vistas: list[str] = []
    herramientas: list[str] = []


class BackupUsuarioItemIn(BaseModel):
    username: str
    email: EmailStr
    password_hash: str
    rol: RolEnum
    nombre_completo: Optional[str] = None
    activo: bool = True
    mfa_habilitado: bool = False
    force_mfa: bool = False
    foto_perfil_url: Optional[str] = None
    email_verificado: bool = False
    permisos: list[str] = []
    vistas: list[str] = []
    herramientas: list[str] = []


class BackupUsuariosIn(BaseModel):
    settings: Optional[ConfiguracionSistemaUpdate] = None
    users: list[BackupUsuarioItemIn]

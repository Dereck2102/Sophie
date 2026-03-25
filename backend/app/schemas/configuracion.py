from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ConfiguracionEmpresaBase(BaseModel):
    timezone: str = Field(default="UTC", description="Timezone de la empresa")
    market: Optional[str] = Field(None, description="Mercado principal")
    require_mfa_global: bool = Field(default=False, description="Requerir MFA autógeno para todos los usuarios")
    session_timeout_minutes: int = Field(default=30, description="Minutos antes de timeout de sesión")
    max_login_attempts: int = Field(default=5, description="Intentos de login fallidos permitidos")
    color_primario: Optional[str] = Field(None, description="Color primario (hex)")
    color_secundario: Optional[str] = Field(None, description="Color secundario (hex)")
    default_iva: float = Field(default=21.0, description="IVA por defecto")
    default_descuento: float = Field(default=0.0, description="Descuento por defecto")
    payphone_key: Optional[str] = Field(None, description="Clave Payphone")
    payphone_secret: Optional[str] = Field(None, description="Secreto Payphone")
    stripe_key: Optional[str] = Field(None, description="Clave Stripe")


class ConfiguracionEmpresaCreate(ConfiguracionEmpresaBase):
    id_cliente: int


class ConfiguracionEmpresaUpdate(BaseModel):
    timezone: Optional[str] = None
    market: Optional[str] = None
    require_mfa_global: Optional[bool] = None
    session_timeout_minutes: Optional[int] = None
    max_login_attempts: Optional[int] = None
    color_primario: Optional[str] = None
    color_secundario: Optional[str] = None
    default_iva: Optional[float] = None
    default_descuento: Optional[float] = None
    payphone_key: Optional[str] = None
    payphone_secret: Optional[str] = None
    stripe_key: Optional[str] = None


class ConfiguracionEmpresaResponse(ConfiguracionEmpresaBase):
    id_config: int
    id_cliente: int
    fecha_creacion: datetime
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True


class ConfiguracionUsuarioBase(BaseModel):
    preferencia_idioma: str = Field(default="es", description="Idioma preferido (es/en)")
    tema: str = Field(default="system", description="Tema (light/dark/system)")
    notificaciones_email: bool = Field(default=True, description="Recibir notificaciones por email")
    notificaciones_sms: bool = Field(default=False, description="Recibir notificaciones por SMS")
    timezone_personal: Optional[str] = Field(None, description="Timezone personal del usuario")
    reporte_footer: Optional[str] = Field(None, description="Pie de página personalizado para reportes")


class ConfiguracionUsuarioCreate(ConfiguracionUsuarioBase):
    id_usuario: int


class ConfiguracionUsuarioUpdate(BaseModel):
    preferencia_idioma: Optional[str] = None
    tema: Optional[str] = None
    notificaciones_email: Optional[bool] = None
    notificaciones_sms: Optional[bool] = None
    timezone_personal: Optional[str] = None
    reporte_footer: Optional[str] = None


class ConfiguracionUsuarioResponse(ConfiguracionUsuarioBase):
    id_config: int
    id_usuario: int
    fecha_actualizacion: datetime

    class Config:
        from_attributes = True

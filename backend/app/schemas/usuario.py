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


class UsuarioSelfUpdate(BaseModel):
    """Schema for users updating their own profile."""
    nombre_completo: Optional[str] = None
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UsuarioOut(UsuarioBase):
    id_usuario: int
    activo: bool
    mfa_habilitado: bool
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

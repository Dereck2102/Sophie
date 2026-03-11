from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CredencialCreate(BaseModel):
    id_empresa: int
    nombre: str
    usuario_acceso: Optional[str] = None
    password_plain: str  # Will be encrypted before storing
    url: Optional[str] = None
    notas: Optional[str] = None


class CredencialUpdate(BaseModel):
    nombre: Optional[str] = None
    usuario_acceso: Optional[str] = None
    password_plain: Optional[str] = None
    url: Optional[str] = None
    notas: Optional[str] = None


class CredencialOut(BaseModel):
    id_credencial: int
    id_empresa: int
    nombre: str
    usuario_acceso: Optional[str] = None
    url: Optional[str] = None
    notas: Optional[str] = None
    # password_plain only returned when explicitly requested and MFA validated

    model_config = {"from_attributes": True}


class CredencialWithPassword(CredencialOut):
    password_plain: str

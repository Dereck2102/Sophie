from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_, cast, delete, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles, require_superadmin
from app.core.access import dumps_json_list, get_effective_access
from app.core.config import get_settings
from app.core.database import get_db
from app.infrastructure.models.auditoria import LogAuditoria
from app.infrastructure.models.cliente import Empresa
from app.infrastructure.models.sistema import ConfiguracionSistema
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.services.email_service import EmailDeliveryError, send_email_message
from app.services.sms_service import SmsDeliveryError, send_sms_message
from app.schemas.usuario import (
    AuditoriaLogOut,
    BackupUsuariosIn,
    BackupUsuariosOut,
    BackupUsuarioItemOut,
    ConfiguracionSistemaOut,
    ConfiguracionSistemaUpdate,
    UsuarioOut,
)

router = APIRouter(prefix="/admin", tags=["Administración Global"])
settings = get_settings()


class AuthChannelsStatusOut(BaseModel):
    twofa_env_enabled: bool
    twofa_enabled: bool
    channel_email_enabled: bool
    channel_sms_enabled: bool
    channel_app_enabled: bool
    smtp_configured: bool
    twilio_configured: bool
    email_effective: bool
    sms_effective: bool
    app_effective: bool


class TestEmailIn(BaseModel):
    to_email: EmailStr | None = None


class TestSmsIn(BaseModel):
    to_phone: str


def _serialize_user(user: Usuario) -> UsuarioOut:
    access = get_effective_access(user)
    return UsuarioOut(
        id_usuario=user.id_usuario,
        username=user.username,
        email=user.email,
        rol=user.rol,
        nombre_completo=user.nombre_completo,
        activo=user.activo,
        mfa_habilitado=user.mfa_habilitado,
        force_mfa=user.force_mfa,
        foto_perfil_url=user.foto_perfil_url,
        email_verificado=user.email_verificado,
        permisos=access["permissions"],
        vistas=access["views"],
        herramientas=access["tools"],
        fecha_creacion=user.fecha_creacion,
    )


async def _get_or_create_settings(db: AsyncSession) -> ConfiguracionSistema:
    result = await db.execute(select(ConfiguracionSistema).where(ConfiguracionSistema.id_configuracion == 1))
    settings = result.scalar_one_or_none()
    if settings:
        return settings
    settings = ConfiguracionSistema(id_configuracion=1)
    db.add(settings)
    await db.flush()
    return settings


@router.get("/settings", response_model=ConfiguracionSistemaOut)
async def get_settings(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> ConfiguracionSistema:
    return await _get_or_create_settings(db)


@router.get("/settings/public", response_model=ConfiguracionSistemaOut)
async def get_public_settings(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConfiguracionSistema:
    return await _get_or_create_settings(db)


@router.patch("/settings", response_model=ConfiguracionSistemaOut)
async def update_settings(
    body: ConfiguracionSistemaUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> ConfiguracionSistema:
    settings = await _get_or_create_settings(db)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(settings, key, value)
    await db.flush()
    return settings


@router.get("/auth/channels/status", response_model=AuthChannelsStatusOut)
async def get_auth_channels_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> AuthChannelsStatusOut:
    system_settings = await _get_or_create_settings(db)
    smtp_configured = bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)
    twilio_configured = bool(
        settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_PHONE
    )

    email_effective = bool(system_settings.auth_channel_email_enabled and smtp_configured)
    sms_effective = bool(system_settings.auth_channel_sms_enabled and twilio_configured)
    app_effective = bool(system_settings.auth_channel_app_enabled)

    return AuthChannelsStatusOut(
        twofa_env_enabled=bool(settings.TWOFA_ENABLED),
        twofa_enabled=bool(system_settings.auth_twofa_enabled),
        channel_email_enabled=bool(system_settings.auth_channel_email_enabled),
        channel_sms_enabled=bool(system_settings.auth_channel_sms_enabled),
        channel_app_enabled=bool(system_settings.auth_channel_app_enabled),
        smtp_configured=smtp_configured,
        twilio_configured=twilio_configured,
        email_effective=email_effective,
        sms_effective=sms_effective,
        app_effective=app_effective,
    )


@router.post("/auth/channels/test-email")
async def test_auth_channel_email(
    body: TestEmailIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> dict[str, str]:
    destination = body.to_email or current_user.email
    if not destination:
        raise HTTPException(status_code=400, detail="Debes indicar un correo de destino")

    try:
        send_email_message(
            to_email=str(destination),
            subject="Prueba de canal de autenticación - SOPHIE",
            text_body=(
                "Este es un correo de prueba del canal de autenticación en SOPHIE.\n"
                "Si recibes este mensaje, el canal EMAIL está funcionando correctamente."
            ),
        )
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=503, detail=f"Fallo al enviar correo de prueba: {exc}")

    return {"detail": f"Correo de prueba enviado a {destination}"}


@router.post("/auth/channels/test-sms")
async def test_auth_channel_sms(
    body: TestSmsIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> dict[str, str]:
    phone = body.to_phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Debes indicar un número de teléfono")

    try:
        send_sms_message(
            to_phone=phone,
            body="SOPHIE: prueba de canal SMS completada correctamente.",
        )
    except SmsDeliveryError as exc:
        raise HTTPException(status_code=503, detail=f"Fallo al enviar SMS de prueba: {exc}")

    return {"detail": f"SMS de prueba enviado a {phone}"}


@router.get("/auditoria", response_model=list[AuditoriaLogOut])
async def list_auditoria(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.SUPERADMIN, RolEnum.ADMIN))],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    modulo: str | None = Query(None),
    id_usuario: int | None = Query(None),
    id_cliente: int | None = Query(None),
    accion_tipo: str | None = Query(None),
    accion_nombre: str | None = Query(None),
    ip_origen: str | None = Query(None),
    fecha_desde: datetime | None = Query(None),
    fecha_hasta: datetime | None = Query(None),
    q: str | None = Query(None),
) -> list[AuditoriaLogOut]:
    tenant_id = current_user.id_cliente or current_user.id_empresa
    is_superadmin = current_user.rol == RolEnum.SUPERADMIN

    if not is_superadmin:
        if tenant_id is None:
            raise HTTPException(status_code=403, detail="Tu usuario admin no está asociado a una empresa")
        if id_cliente is not None and id_cliente != tenant_id:
            raise HTTPException(status_code=403, detail="No puedes consultar auditoría de otra empresa")
        id_cliente = tenant_id

    query = (
        select(LogAuditoria, Usuario.username, Usuario.nombre_completo, Empresa.razon_social)
        .outerjoin(Usuario, Usuario.id_usuario == LogAuditoria.id_usuario)
        .outerjoin(Empresa, Empresa.id_cliente == LogAuditoria.id_cliente)
        .order_by(LogAuditoria.fecha.desc())
        .offset(skip)
        .limit(limit)
    )

    filters = []
    if modulo:
        filters.append(LogAuditoria.modulo == modulo)
    if id_usuario is not None:
        filters.append(LogAuditoria.id_usuario == id_usuario)
    if id_cliente is not None:
        filters.append(LogAuditoria.id_cliente == id_cliente)
    if accion_tipo:
        filters.append(LogAuditoria.accion_tipo == accion_tipo)
    if accion_nombre:
        filters.append(LogAuditoria.accion_nombre.ilike(f"%{accion_nombre}%"))
    if ip_origen:
        filters.append(LogAuditoria.ip_origen.ilike(f"%{ip_origen}%"))
    if fecha_desde:
        filters.append(LogAuditoria.fecha >= fecha_desde)
    if fecha_hasta:
        filters.append(LogAuditoria.fecha <= fecha_hasta)
    if q:
        query_text = f"%{q.strip()}%"
        filters.append(
            or_(
                LogAuditoria.accion.ilike(query_text),
                LogAuditoria.accion_nombre.ilike(query_text),
                LogAuditoria.accion_tipo.ilike(query_text),
                LogAuditoria.modulo.ilike(query_text),
                LogAuditoria.ip_origen.ilike(query_text),
                LogAuditoria.ruta.ilike(query_text),
                cast(LogAuditoria.id_usuario, String).ilike(query_text),
                cast(LogAuditoria.id_cliente, String).ilike(query_text),
                Usuario.username.ilike(query_text),
                Usuario.nombre_completo.ilike(query_text),
                Empresa.razon_social.ilike(query_text),
            )
        )

    if filters:
        query = query.where(and_(*filters))

    result = await db.execute(query)
    rows = result.all()

    return [
        AuditoriaLogOut(
            id_log=log.id_log,
            id_cliente=log.id_cliente,
            empresa_nombre=empresa_nombre,
            id_usuario=log.id_usuario,
            usuario_username=username,
            usuario_nombre=nombre_completo,
            accion=log.accion,
            accion_tipo=log.accion_tipo,
            accion_nombre=log.accion_nombre,
            modulo=log.modulo,
            metodo_http=log.metodo_http,
            ruta=log.ruta,
            ip_origen=log.ip_origen,
            user_agent=log.user_agent,
            pais_origen=log.pais_origen,
            ciudad_origen=log.ciudad_origen,
            ubicacion_aprox=log.ubicacion_aprox,
            detalle=log.detalle,
            fecha=log.fecha,
        )
        for log, username, nombre_completo, empresa_nombre in rows
    ]


@router.get("/backup/usuarios", response_model=BackupUsuariosOut)
async def backup_usuarios(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> BackupUsuariosOut:
    settings = await _get_or_create_settings(db)
    result = await db.execute(select(Usuario).order_by(Usuario.id_usuario))
    users = result.scalars().all()
    return BackupUsuariosOut(
        generated_at=datetime.now(timezone.utc),
        settings=settings,
        users=[
            BackupUsuarioItemOut(
                username=user.username,
                email=user.email,
                password_hash=user.password_hash,
                rol=user.rol,
                nombre_completo=user.nombre_completo,
                activo=user.activo,
                mfa_habilitado=user.mfa_habilitado,
                force_mfa=user.force_mfa,
                foto_perfil_url=user.foto_perfil_url,
                email_verificado=user.email_verificado,
                permisos=get_effective_access(user)["permissions"],
                vistas=get_effective_access(user)["views"],
                herramientas=get_effective_access(user)["tools"],
            )
            for user in users
        ],
    )


@router.post("/restore/usuarios", status_code=status.HTTP_200_OK)
async def restore_usuarios(
    body: BackupUsuariosIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_superadmin())],
) -> dict[str, str]:
    if not body.users:
        raise HTTPException(status_code=400, detail="La copia debe incluir al menos un usuario")

    await db.execute(delete(Usuario))
    await db.flush()

    for item in body.users:
        user = Usuario(
            username=item.username,
            email=item.email,
            password_hash=item.password_hash,
            rol=item.rol,
            nombre_completo=item.nombre_completo,
            activo=item.activo,
            mfa_habilitado=item.mfa_habilitado,
            force_mfa=item.force_mfa,
            foto_perfil_url=item.foto_perfil_url,
            email_verificado=item.email_verificado,
            permisos_json=dumps_json_list(item.permisos),
            vistas_json=dumps_json_list(item.vistas),
            herramientas_json=dumps_json_list(item.herramientas),
        )
        db.add(user)

    settings = await _get_or_create_settings(db)
    if body.settings is not None:
        for key, value in body.settings.model_dump(exclude_none=True).items():
            setattr(settings, key, value)

    await db.flush()
    return {"detail": "Usuarios y configuración restaurados correctamente"}
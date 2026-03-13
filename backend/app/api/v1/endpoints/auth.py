from __future__ import annotations

import base64
import io
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import qrcode
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_client_ip
from app.core.access import get_effective_access
from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import (
    consume_recovery_code,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_recovery_codes,
    generate_totp_secret,
    get_totp_uri,
    hash_one_time_secret,
    hash_password,
    verify_password,
    verify_totp,
)
from app.infrastructure.models.auditoria import LogAuditoria
from app.infrastructure.models.sistema import ConfiguracionSistema
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.services.email_service import EmailDeliveryError, send_mfa_email_code
from app.schemas.usuario import (
    LoginRequest,
    MFASetupOut,
    MFAVerifyRequest,
    EmailVerificationRequest,
    EmailVerificationTokenOut,
    PasswordRecoveryConfirmRequest,
    PasswordRecoveryRequest,
    RefreshRequest,
    RecoveryCodesOut,
    RecoveryCodesRotateRequest,
    TokenResponse,
    UsuarioCreate,
    UsuarioOut,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not local or not domain:
        return "correo no disponible"
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[:2] + "*" * (len(local) - 2)
    return f"{masked_local}@{domain}"


def _to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


async def _issue_mfa_email_code(user: Usuario, db: AsyncSession, ip: str) -> tuple[str | None, str | None]:
    if not user.email:
        raise HTTPException(status_code=400, detail="La cuenta no tiene correo para MFA por email")

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_minutes = max(int(settings.MFA_EMAIL_CODE_EXPIRE_MINUTES or 10), 1)
    user.mfa_email_code_hash = hash_one_time_secret(code)
    user.mfa_email_code_expira = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    user.mfa_email_code_intentos = 0
    await db.flush()

    db.add(
        LogAuditoria(
            id_usuario=user.id_usuario,
            accion="MFA_EMAIL_CODE_ISSUED",
            modulo="auth",
            ip_origen=ip,
            detalle={"username": user.username, "destination": _mask_email(user.email)},
        )
    )

    try:
        send_mfa_email_code(user.email, code=code, expires_minutes=expires_minutes)
        return _mask_email(user.email), None
    except EmailDeliveryError:
        if settings.DEBUG or settings.MFA_EMAIL_DEBUG_FALLBACK:
            return _mask_email(user.email), code
        raise HTTPException(status_code=503, detail="No se pudo enviar el código MFA por correo")


async def _verify_mfa_email_code(user: Usuario, code: str, db: AsyncSession) -> bool:
    if not user.mfa_email_code_hash or not user.mfa_email_code_expira:
        return False

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    expires_utc = _to_utc_naive(user.mfa_email_code_expira)
    if expires_utc < now_utc:
        user.mfa_email_code_hash = None
        user.mfa_email_code_expira = None
        user.mfa_email_code_intentos = 0
        await db.flush()
        return False

    attempts = int(user.mfa_email_code_intentos or 0)
    if attempts >= 6:
        user.mfa_email_code_hash = None
        user.mfa_email_code_expira = None
        user.mfa_email_code_intentos = 0
        await db.flush()
        return False

    if hash_one_time_secret(code.strip()) != user.mfa_email_code_hash:
        user.mfa_email_code_intentos = attempts + 1
        await db.flush()
        return False

    user.mfa_email_code_hash = None
    user.mfa_email_code_expira = None
    user.mfa_email_code_intentos = 0
    await db.flush()
    return True


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    ip: Annotated[str, Depends(get_client_ip)],
) -> TokenResponse:
    now = datetime.now(timezone.utc)

    settings_result = await db.execute(
        select(ConfiguracionSistema.max_login_attempts).where(ConfiguracionSistema.id_configuracion == 1)
    )
    max_login_attempts = int(settings_result.scalar_one_or_none() or 5)

    result = await db.execute(select(Usuario).where(Usuario.username == body.username))
    user = result.scalar_one_or_none()
    if user and user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Cuenta bloqueada temporalmente por intentos fallidos. Intenta más tarde.",
        )

    if not user or not verify_password(body.password, user.password_hash):
        if user:
            user.failed_login_attempts = int(user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= max_login_attempts:
                user.locked_until = now + timedelta(minutes=15)
                user.failed_login_attempts = 0
            await db.flush()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not user.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    user.failed_login_attempts = 0
    user.locked_until = None

    mfa_verified = False
    if user.mfa_habilitado:
        if body.mfa_code:
            totp_valid = verify_totp(user.mfa_secret or "", body.mfa_code)
            email_valid = False
            if not totp_valid:
                email_valid = await _verify_mfa_email_code(user, body.mfa_code, db)
            if not (totp_valid or email_valid):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code"
                )
            mfa_verified = True
        elif body.recovery_code:
            stored_codes: list[str] = []
            if user.recovery_codes_json:
                try:
                    loaded = json.loads(user.recovery_codes_json)
                    if isinstance(loaded, list):
                        stored_codes = [str(item) for item in loaded]
                except json.JSONDecodeError:
                    stored_codes = []
            consumed, updated = consume_recovery_code(body.recovery_code, stored_codes)
            if not consumed:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid recovery code",
                )
            user.recovery_codes_json = json.dumps(updated)
            mfa_verified = True
        else:
            destination, debug_code = await _issue_mfa_email_code(user, db, ip)
            return TokenResponse(
                mfa_required=True,
                access_token="",
                mfa_channel="email",
                mfa_destination=destination,
                mfa_debug_code=debug_code,
            )

    access = get_effective_access(user)
    token_data = {
        "sub": str(user.id_usuario),
        "rol": user.rol.value,
        "sid": secrets.token_urlsafe(24),
        "mfa_verified": mfa_verified,
        "permissions": access["permissions"],
        "views": access["views"],
        "tools": access["tools"],
        "rv": int(user.refresh_token_version or 1),
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=7 * 24 * 3600,
    )

    # Audit log
    db.add(
        LogAuditoria(
            id_usuario=user.id_usuario,
            accion="LOGIN",
            modulo="auth",
            ip_origen=ip,
            detalle={"username": user.username},
        )
    )
    await db.flush()

    return TokenResponse(
        access_token=access_token,
        session_id=token_data.get("sid"),
        access_expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
    body: RefreshRequest | None = None,
) -> TokenResponse:
    incoming_refresh = (
        body.refresh_token if body and body.refresh_token else refresh_token_cookie
    )
    if not incoming_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token requerido")

    try:
        payload = decode_token(incoming_refresh)
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    result = await db.execute(
        select(Usuario).where(Usuario.id_usuario == int(payload["sub"]))
    )
    user = result.scalar_one_or_none()
    if not user or not user.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    token_version = int(payload.get("rv") or 1)
    if token_version != int(user.refresh_token_version or 1):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    access = get_effective_access(user)
    token_data = {
        "sub": str(user.id_usuario),
        "rol": user.rol.value,
        "sid": payload.get("sid") or secrets.token_urlsafe(24),
        "mfa_verified": payload.get("mfa_verified", False),
        "permissions": access["permissions"],
        "views": access["views"],
        "tools": access["tools"],
        "rv": int(user.refresh_token_version or 1),
    }
    access_token = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=7 * 24 * 3600,
    )
    return TokenResponse(
        access_token=access_token,
        session_id=token_data.get("sid"),
        access_expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie("refresh_token")
    return {"detail": "Logged out"}


@router.get("/mfa/setup", response_model=MFASetupOut)
async def mfa_setup(
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MFASetupOut:
    if current_user.mfa_habilitado:
        raise HTTPException(status_code=400, detail="MFA already enabled")
    secret = generate_totp_secret()
    current_user.mfa_secret = secret
    await db.flush()

    uri = get_totp_uri(secret, current_user.username)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    return MFASetupOut(secret=secret, uri=uri, qr_image_b64=qr_b64)


@router.post("/mfa/verify")
async def mfa_verify(
    body: MFAVerifyRequest,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA not set up. Call /mfa/setup first.")
    if not verify_totp(current_user.mfa_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    current_user.mfa_habilitado = True
    await db.flush()
    return {"detail": "MFA enabled successfully"}


@router.post("/register", response_model=UsuarioOut, status_code=201)
async def register_first_admin(
    body: UsuarioCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    """Creates the first bootstrap superadmin user. Subsequent users must be created by an admin."""
    result = await db.execute(select(Usuario))
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=403,
            detail="Use /users endpoint to create additional users (admin required)",
        )
    user = Usuario(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        rol=RolEnum.SUPERADMIN,
        nombre_completo=body.nombre_completo,
        email_verificado=True,
    )
    db.add(user)
    await db.flush()
    return user


@router.post("/email/verification-token", response_model=EmailVerificationTokenOut)
async def request_email_verification_token(
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmailVerificationTokenOut:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    current_user.email_verificacion_token = token
    current_user.email_verificacion_expira = expires_at
    await db.flush()
    return EmailVerificationTokenOut(token=token, expires_at=expires_at)


@router.post("/email/verify")
async def verify_email_token(
    body: EmailVerificationRequest,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    if not current_user.email_verificacion_token or not current_user.email_verificacion_expira:
        raise HTTPException(status_code=400, detail="No hay token de verificación activo")
    if current_user.email_verificacion_token != body.token:
        raise HTTPException(status_code=400, detail="Token de verificación inválido")

    expires_at = current_user.email_verificacion_expira
    if expires_at.tzinfo is not None:
        expires_at_utc = expires_at.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        expires_at_utc = expires_at
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    if expires_at_utc < now_utc:
        raise HTTPException(status_code=400, detail="El token ha expirado")

    current_user.email_verificado = True
    current_user.email_verificacion_token = None
    current_user.email_verificacion_expira = None
    await db.flush()
    return {"detail": "Correo verificado correctamente"}


@router.post("/password-recovery/request")
async def request_password_recovery(
    body: PasswordRecoveryRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    ip: Annotated[str, Depends(get_client_ip)],
) -> dict[str, str | None]:
    identifier = body.identifier.strip()
    if not identifier:
        return {"detail": "Si la cuenta existe, se generó un token temporal de recuperación.", "recovery_token": None}

    user_result = await db.execute(
        select(Usuario).where(
            (Usuario.username == identifier)
            | (Usuario.email == identifier)
            | (Usuario.telefono_recuperacion == identifier)
        )
    )
    user = user_result.scalar_one_or_none()
    recovery_token: str | None = None
    if user and user.activo:
        recovery_token = secrets.token_urlsafe(32)
        user.password_reset_token_hash = hash_one_time_secret(recovery_token)
        user.password_reset_expira = datetime.now(timezone.utc) + timedelta(minutes=30)
        user.password_reset_intentos = 0
        db.add(
            LogAuditoria(
                id_usuario=user.id_usuario,
                accion="PASSWORD_RECOVERY_REQUEST",
                modulo="auth",
                ip_origen=ip,
                detalle={"identifier": identifier},
            )
        )
        await db.flush()

    return {
        "detail": "Si la cuenta existe, se generó un token temporal de recuperación.",
        "recovery_token": recovery_token if settings.DEBUG else None,
    }


@router.post("/password-recovery/confirm")
async def confirm_password_recovery(
    body: PasswordRecoveryConfirmRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    ip: Annotated[str, Depends(get_client_ip)],
) -> dict[str, str]:
    token_hash = hash_one_time_secret(body.token)
    user_result = await db.execute(
        select(Usuario).where(Usuario.password_reset_token_hash == token_hash)
    )
    user = user_result.scalar_one_or_none()
    if not user or not user.password_reset_expira:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    expires_at = user.password_reset_expira
    if expires_at.tzinfo is not None:
        expires_at_utc = expires_at.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        expires_at_utc = expires_at
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    if expires_at_utc < now_utc:
        user.password_reset_token_hash = None
        user.password_reset_expira = None
        user.password_reset_intentos = 0
        await db.flush()
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    if int(user.password_reset_intentos or 0) >= 5:
        user.password_reset_token_hash = None
        user.password_reset_expira = None
        user.password_reset_intentos = 0
        await db.flush()
        raise HTTPException(status_code=429, detail="Token bloqueado por demasiados intentos")

    user.password_hash = hash_password(body.new_password)
    user.password_reset_token_hash = None
    user.password_reset_expira = None
    user.password_reset_intentos = 0
    user.refresh_token_version = int(user.refresh_token_version or 1) + 1
    user.ultima_rotacion_password = datetime.now(timezone.utc)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(
        LogAuditoria(
            id_usuario=user.id_usuario,
            accion="PASSWORD_RECOVERY_CONFIRM",
            modulo="auth",
            ip_origen=ip,
            detalle={"username": user.username},
        )
    )
    await db.flush()
    return {"detail": "Contraseña actualizada correctamente"}


@router.post("/mfa/recovery-codes/rotate", response_model=RecoveryCodesOut)
async def rotate_mfa_recovery_codes(
    body: RecoveryCodesRotateRequest,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecoveryCodesOut:
    if not current_user.mfa_habilitado:
        raise HTTPException(status_code=400, detail="Debes habilitar MFA antes de generar códigos de recuperación")
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    plain_codes, hashed_codes = generate_recovery_codes()
    current_user.recovery_codes_json = json.dumps(hashed_codes)
    generated_at = datetime.now(timezone.utc)
    await db.flush()
    return RecoveryCodesOut(codes=plain_codes, generated_at=generated_at)

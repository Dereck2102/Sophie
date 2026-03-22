from __future__ import annotations

import base64
import io
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import qrcode
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
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
from app.services.email_service import (
    EmailDeliveryError,
    send_email_verification_token,
    send_mfa_email_code,
    send_password_recovery_email,
)
from app.services.sms_service import SmsDeliveryError, send_mfa_sms_code
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


def _mask_phone(phone: str) -> str:
    """Show first 3 chars (country code) and last 3 digits; mask middle."""
    clean = "".join(c for c in phone.strip() if not c.isspace())
    if len(clean) <= 6:
        return clean
    return clean[:3] + "*" * (len(clean) - 6) + clean[-3:]


def _normalize_user_agent(raw: str | None) -> str:
    return (raw or "unknown")[:300]


def _is_suspicious_login(user: Usuario, *, ip: str, user_agent: str) -> bool:
    if not user.last_login_ip and not user.last_login_user_agent:
        return False

    ip_changed = bool(user.last_login_ip and user.last_login_ip != ip)
    ua_changed = bool(user.last_login_user_agent and user.last_login_user_agent != user_agent)
    return ip_changed or ua_changed


async def _issue_mfa_code(
    user: Usuario,
    db: AsyncSession,
    ip: str,
    *,
    allow_email: bool,
    allow_sms: bool,
) -> tuple[str, str | None, str | None, str | None]:
    """Generate an OTP, attempt delivery via email and/or SMS.

    Returns:
        (channel, email_destination, phone_destination, debug_code)
        channel is one of: "email", "sms", "email+sms"
        debug_code is set only when delivery failed and debug fallback is enabled.
    """
    if not allow_email and not allow_sms:
        raise HTTPException(status_code=400, detail="No hay canales OTP habilitados")

    if (allow_email and not user.email) and (allow_sms and not user.telefono_recuperacion):
        raise HTTPException(
            status_code=400,
            detail="La cuenta no tiene correo ni teléfono para el envío del código 2FA",
        )

    if allow_email and not user.email and not allow_sms:
        raise HTTPException(status_code=400, detail="La cuenta no tiene correo para el envío del código 2FA")

    if allow_sms and not user.telefono_recuperacion and not allow_email:
        raise HTTPException(status_code=400, detail="La cuenta no tiene teléfono para el envío del código 2FA")

    if not user.email and not user.telefono_recuperacion:
        raise HTTPException(
            status_code=400,
            detail="La cuenta no tiene correo ni teléfono para el envío del código 2FA",
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    expires_minutes = max(int(settings.MFA_EMAIL_CODE_EXPIRE_MINUTES or 10), 1)
    user.mfa_email_code_hash = hash_one_time_secret(code)
    user.mfa_email_code_expira = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    user.mfa_email_code_intentos = 0
    await db.flush()

    db.add(
        LogAuditoria(
            id_usuario=user.id_usuario,
            accion="MFA_CODE_ISSUED",
            modulo="auth",
            ip_origen=ip,
            detalle={
                "username": user.username,
                "email": _mask_email(user.email) if user.email else None,
                "phone": _mask_phone(user.telefono_recuperacion) if user.telefono_recuperacion else None,
            },
        )
    )

    use_fallback = settings.DEBUG or settings.MFA_EMAIL_DEBUG_FALLBACK
    debug_code: str | None = None
    email_dest: str | None = None
    phone_dest: str | None = None

    # ── Email channel ────────────────────────────────────────────────────────────
    if allow_email and user.email:
        try:
            send_mfa_email_code(user.email, code=code, expires_minutes=expires_minutes)
            email_dest = _mask_email(user.email)
        except EmailDeliveryError:
            if use_fallback:
                email_dest = _mask_email(user.email)
                debug_code = code

    # ── SMS channel ──────────────────────────────────────────────────────────────
    if allow_sms and user.telefono_recuperacion:
        try:
            send_mfa_sms_code(user.telefono_recuperacion, code=code, expires_minutes=expires_minutes)
            phone_dest = _mask_phone(user.telefono_recuperacion)
        except SmsDeliveryError:
            if use_fallback:
                phone_dest = _mask_phone(user.telefono_recuperacion)
                debug_code = debug_code or code

    if not email_dest and not phone_dest:
        raise HTTPException(
            status_code=503,
            detail="No se pudo enviar el código 2FA por ningún canal",
        )

    channels: list[str] = []
    if email_dest:
        channels.append("email")
    if phone_dest:
        channels.append("sms")
    channel = "+".join(channels)  # "email", "sms", or "email+sms"

    return channel, email_dest, phone_dest, debug_code


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
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    ip: Annotated[str, Depends(get_client_ip)],
) -> TokenResponse:
    now = datetime.now(timezone.utc)
    now_utc_naive = now.replace(tzinfo=None)

    settings_result = await db.execute(
        select(ConfiguracionSistema).where(ConfiguracionSistema.id_configuracion == 1)
    )
    system_settings = settings_result.scalar_one_or_none()
    max_login_attempts = int(system_settings.max_login_attempts if system_settings else 5)

    result = await db.execute(select(Usuario).where(Usuario.username == body.username))
    user = result.scalar_one_or_none()
    if user and user.locked_until and _to_utc_naive(user.locked_until) > now_utc_naive:
        db.add(
            LogAuditoria(
                id_usuario=user.id_usuario,
                accion="LOGIN_BLOCKED",
                modulo="auth",
                ip_origen=ip,
                detalle={"username": body.username},
            )
        )
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Cuenta bloqueada temporalmente por intentos fallidos. Intenta más tarde.",
        )

    if not user or not verify_password(body.password, user.password_hash):
        next_attempts = 1
        locked = False
        if user:
            next_attempts = int(user.failed_login_attempts or 0) + 1
            user.failed_login_attempts = next_attempts
            if next_attempts >= max_login_attempts:
                user.locked_until = now + timedelta(minutes=15)
                user.failed_login_attempts = 0
                locked = True
            db.add(
                LogAuditoria(
                    id_usuario=user.id_usuario,
                    accion="LOGIN_FAILED",
                    modulo="auth",
                    ip_origen=ip,
                    detalle={
                        "username": body.username,
                        "attempts": next_attempts,
                        "locked": locked,
                    },
                )
            )
        else:
            db.add(
                LogAuditoria(
                    id_usuario=None,
                    accion="LOGIN_FAILED",
                    modulo="auth",
                    ip_origen=ip,
                    detalle={
                        "username": body.username,
                        "attempts": next_attempts,
                        "locked": False,
                        "reason": "unknown_user",
                    },
                )
            )
            await db.flush()
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not user.activo:
        db.add(
            LogAuditoria(
                id_usuario=user.id_usuario,
                accion="LOGIN_DISABLED",
                modulo="auth",
                ip_origen=ip,
                detalle={"username": body.username},
            )
        )
        await db.flush()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    user.failed_login_attempts = 0
    user.locked_until = None
    current_user_agent = _normalize_user_agent(request.headers.get("user-agent"))

    require_mfa_global = bool(system_settings.require_mfa_global) if system_settings else False
    auth_twofa_enabled = bool(system_settings.auth_twofa_enabled) if system_settings else True
    allow_email = bool(system_settings.auth_channel_email_enabled) if system_settings else True
    allow_sms = bool(system_settings.auth_channel_sms_enabled) if system_settings else True
    allow_app = bool(system_settings.auth_channel_app_enabled) if system_settings else True
    suspicious_login = _is_suspicious_login(user, ip=ip, user_agent=current_user_agent)
    if suspicious_login:
        user.refresh_token_version = int(user.refresh_token_version or 1) + 1
        db.add(
            LogAuditoria(
                id_usuario=user.id_usuario,
                accion="LOGIN_RISK_DETECTED",
                modulo="auth",
                ip_origen=ip,
                detalle={
                    "username": user.username,
                    "last_login_ip": user.last_login_ip,
                    "current_ip": ip,
                    "last_user_agent": user.last_login_user_agent,
                    "current_user_agent": current_user_agent,
                },
            )
        )

    twofa_verified = False
    requires_step_up = suspicious_login and auth_twofa_enabled
    if auth_twofa_enabled and (require_mfa_global or user.mfa_habilitado or requires_step_up):
        if body.mfa_code:
            code_valid = False
            if allow_app and user.mfa_secret:
                code_valid = verify_totp(user.mfa_secret, body.mfa_code)
            if not code_valid and (allow_email or allow_sms):
                code_valid = await _verify_mfa_email_code(user, body.mfa_code, db)
            if not code_valid:
                await db.flush()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Código 2FA incorrecto o expirado"
                )
            twofa_verified = True
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
                await db.flush()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid recovery code",
                )
            user.recovery_codes_json = json.dumps(updated)
            twofa_verified = True
        else:
            if allow_email or allow_sms:
                try:
                    channel, email_dest, phone_dest, debug_code = await _issue_mfa_code(
                        user,
                        db,
                        ip,
                        allow_email=allow_email,
                        allow_sms=allow_sms,
                    )
                    return TokenResponse(
                        mfa_required=True,
                        access_token="",
                        mfa_channel=channel,
                        mfa_destination=email_dest,
                        mfa_phone_destination=phone_dest,
                        mfa_debug_code=debug_code,
                    )
                except HTTPException:
                    if allow_app and user.mfa_secret:
                        return TokenResponse(mfa_required=True, access_token="", mfa_channel="app")
                    raise

            if allow_app and user.mfa_secret:
                return TokenResponse(mfa_required=True, access_token="", mfa_channel="app")

            raise HTTPException(status_code=503, detail="No hay canales 2FA habilitados para esta cuenta")

    user.last_login_at = datetime.now(timezone.utc)
    user.last_login_ip = ip
    user.last_login_user_agent = current_user_agent

    access = get_effective_access(user)
    token_data = {
        "sub": str(user.id_usuario),
        "rol": user.rol.value,
        "sid": secrets.token_urlsafe(24),
        "mfa_verified": twofa_verified,
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

    user.refresh_token_version = int(user.refresh_token_version or 1) + 1

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

    if current_user.email:
        try:
            send_email_verification_token(current_user.email, verification_token=token, expires_hours=24)
        except EmailDeliveryError:
            if not (settings.DEBUG or settings.MFA_EMAIL_DEBUG_FALLBACK):
                raise HTTPException(status_code=503, detail="No se pudo enviar el correo de verificación")

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

        if user.email:
            try:
                send_password_recovery_email(user.email, recovery_token=recovery_token, expires_minutes=30)
            except EmailDeliveryError:
                if not (settings.DEBUG or settings.MFA_EMAIL_DEBUG_FALLBACK):
                    raise HTTPException(status_code=503, detail="No se pudo enviar el correo de recuperación")

    return {
        "detail": "Si la cuenta existe, se generó un token temporal de recuperación.",
        "recovery_token": recovery_token if (settings.DEBUG or settings.MFA_EMAIL_DEBUG_FALLBACK) else None,
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

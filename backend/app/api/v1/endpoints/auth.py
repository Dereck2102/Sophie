from __future__ import annotations

import base64
import io
from typing import Annotated

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_client_ip
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_totp_secret,
    get_totp_uri,
    hash_password,
    verify_password,
    verify_totp,
)
from app.infrastructure.models.auditoria import LogAuditoria
from app.infrastructure.models.usuario import Usuario
from app.schemas.usuario import (
    LoginRequest,
    MFASetupOut,
    MFAVerifyRequest,
    RefreshRequest,
    TokenResponse,
    UsuarioCreate,
    UsuarioOut,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    ip: Annotated[str, Depends(get_client_ip)],
) -> TokenResponse:
    result = await db.execute(select(Usuario).where(Usuario.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not user.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    mfa_verified = False
    if user.mfa_habilitado:
        if not body.mfa_code:
            return TokenResponse(mfa_required=True, access_token="")
        if not verify_totp(user.mfa_secret or "", body.mfa_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code"
            )
        mfa_verified = True

    token_data = {"sub": str(user.id_usuario), "rol": user.rol.value, "mfa_verified": mfa_verified}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
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

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
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

    token_data = {"sub": str(user.id_usuario), "rol": user.rol.value, "mfa_verified": payload.get("mfa_verified", False)}
    access_token = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 3600,
    )
    return TokenResponse(access_token=access_token)


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
    """Creates the first admin user. Subsequent users must be created by an admin."""
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
        rol=body.rol,
        nombre_completo=body.nombre_completo,
    )
    db.add(user)
    await db.flush()
    return user

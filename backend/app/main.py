from __future__ import annotations

import ipaddress
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, ensure_development_schema, engine
from app.core.security import decode_token
from app.infrastructure.models.auditoria import LogAuditoria
from app.infrastructure.models.usuario import Usuario
from app.infrastructure.models import *  # noqa: F401,F403 - register all models

settings = get_settings()


class _InMemoryRateLimiter:
    def __init__(self, window_seconds: int):
        self.window_seconds = max(window_seconds, 1)
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int) -> bool:
        if limit <= 0:
            return True
        now = time.monotonic()
        bucket = self._buckets[key]
        window_start = now - self.window_seconds
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


rate_limiter = _InMemoryRateLimiter(settings.RATE_LIMIT_WINDOW_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (for development; use Alembic in production)
    from app.core.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ensure_development_schema()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SOPHIE ERP - Big Solutions",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.GZIP_ENABLED:
    app.add_middleware(GZipMiddleware, minimum_size=settings.GZIP_MINIMUM_SIZE)

if settings.TRUSTED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)

app.include_router(api_router)

if settings.METRICS_ENABLED:
    Instrumentator(excluded_handlers=["/health", settings.METRICS_PATH]).instrument(app).expose(
        app,
        endpoint=settings.METRICS_PATH,
        include_in_schema=False,
    )


@app.middleware("http")
async def security_shield(request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit():
        if int(content_length) > settings.REQUEST_BODY_MAX_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Payload demasiado grande"},
            )

    if settings.RATE_LIMIT_ENABLED:
        ip = _extract_client_ip(request) or "unknown"
        path = request.url.path.lower()
        is_sensitive = "/auth/" in path or "/payphone/webhook" in path
        limit = settings.RATE_LIMIT_AUTH_MAX_REQUESTS if is_sensitive else settings.RATE_LIMIT_MAX_REQUESTS
        scope = "sensitive" if is_sensitive else "default"
        if not rate_limiter.allow(f"{ip}:{scope}", limit):
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(settings.RATE_LIMIT_WINDOW_SECONDS)},
                content={"detail": "Demasiadas solicitudes. Intenta nuevamente en unos segundos."},
            )

    response = await call_next(request)

    if settings.SECURITY_HEADERS_ENABLED:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        if not settings.DEBUG:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    return response


def _extract_client_ip(request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_ip = forwarded_for.split(",", 1)[0].strip()
        if first_ip:
            return first_ip
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else None


def _resolve_ip_location(ip: str | None) -> tuple[str | None, str | None, str | None]:
    if not ip:
        return None, None, None
    try:
        parsed = ipaddress.ip_address(ip)
        if parsed.is_loopback:
            return "Local", "Loopback", "Servidor local"
        if parsed.is_private:
            return "Local", "Red privada", "Red interna / VPN"
        return None, None, "IP pública (geolocalización exacta no configurada)"
    except ValueError:
        return None, None, None


def _normalize_action(method: str, path: str, status_code: int, has_query: bool) -> tuple[str, str]:
    method_u = method.upper()
    path_l = path.lower()

    if "/auth/login" in path_l:
        if status_code < 400:
            return "login", "Inicio de sesión"
        return "login_failed", "Intento de inicio de sesión fallido"
    if "/auth/logout" in path_l:
        return "logout", "Cierre de sesión"

    if method_u == "POST":
        return "crear", "Creación de registro"
    if method_u in {"PUT", "PATCH"}:
        return "modificar", "Edición / modificación"
    if method_u == "DELETE":
        return "eliminar", "Eliminación de registro"
    if method_u == "GET":
        if has_query:
            return "buscar", "Búsqueda / filtrado"
        return "consultar", "Consulta de datos"
    return "accion", f"Acción {method_u}"


@app.middleware("http")
async def audit_requests(request, call_next):
    path = request.url.path
    if path in {"/health", "/openapi.json"} or path.startswith("/docs") or path.startswith("/redoc"):
        return await call_next(request)

    started = time.perf_counter()
    status_code = 500
    response = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        try:
            auth_header = request.headers.get("Authorization", "")
            user_id = None
            id_cliente = None
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]
                try:
                    payload = decode_token(token)
                    user_id = int(payload.get("sub")) if payload.get("sub") else None
                except ValueError:
                    user_id = None

            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            modulo = path.strip("/").split("/")
            modulo_name = modulo[2] if len(modulo) >= 3 else (modulo[0] if modulo and modulo[0] else "root")
            ip_origen = _extract_client_ip(request)
            pais_origen, ciudad_origen, ubicacion_aprox = _resolve_ip_location(ip_origen)
            accion_tipo, accion_nombre = _normalize_action(
                request.method,
                path,
                status_code,
                has_query=bool(request.query_params),
            )

            async with AsyncSessionLocal() as session:
                if user_id is not None:
                    user_result = await session.execute(select(Usuario.id_cliente).where(Usuario.id_usuario == user_id))
                    id_cliente = user_result.scalar_one_or_none()
                session.add(
                    LogAuditoria(
                        id_cliente=id_cliente,
                        id_usuario=user_id,
                        accion=f"{request.method} {path}",
                        accion_tipo=accion_tipo,
                        accion_nombre=accion_nombre,
                        modulo=modulo_name,
                        metodo_http=request.method,
                        ruta=path,
                        ip_origen=ip_origen,
                        user_agent=(request.headers.get("user-agent") or "")[:300] or None,
                        pais_origen=pais_origen,
                        ciudad_origen=ciudad_origen,
                        ubicacion_aprox=ubicacion_aprox,
                        detalle={
                            "query": dict(request.query_params),
                            "status_code": status_code,
                            "duration_ms": duration_ms,
                            "accion_tipo": accion_tipo,
                            "accion_nombre": accion_nombre,
                        },
                    )
                )
                await session.commit()
        except Exception:
            pass


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}

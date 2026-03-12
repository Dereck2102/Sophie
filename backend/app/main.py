from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, ensure_development_schema, engine
from app.core.security import decode_token
from app.infrastructure.models.auditoria import LogAuditoria
from app.infrastructure.models import *  # noqa: F401,F403 - register all models

settings = get_settings()


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
    description="SOPHIE ERP/CRM - Big Solutions",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


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

            async with AsyncSessionLocal() as session:
                session.add(
                    LogAuditoria(
                        id_usuario=user_id,
                        accion=f"{request.method} {path}",
                        modulo=modulo_name,
                        ip_origen=request.client.host if request.client else None,
                        detalle={
                            "query": dict(request.query_params),
                            "status_code": status_code,
                            "duration_ms": duration_ms,
                        },
                    )
                )
                await session.commit()
        except Exception:
            pass


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}

from fastapi import APIRouter

from app.core.config import get_settings

from app.api.v1.endpoints import (
    admin,
    auth,
    boveda as credenciales,
    caja_chica,
    clientes,
    compras,
    dashboard,
    global_admin,
    images,
    inventario,
    proyectos,
    public,
    subscriptions,
    tickets,
    usuarios,
    ventas,
)

api_router = APIRouter(prefix="/api/v1")
settings = get_settings()

api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(public.router)
api_router.include_router(global_admin.router)
api_router.include_router(dashboard.router)
if settings.ENABLE_CRM_MODULE:
    api_router.include_router(clientes.router)
api_router.include_router(ventas.router)
api_router.include_router(compras.router)
api_router.include_router(inventario.router)
api_router.include_router(tickets.router)
api_router.include_router(proyectos.router)
api_router.include_router(credenciales.router)
if settings.ENABLE_CAJA_CHICA_MODULE:
    api_router.include_router(caja_chica.router)
api_router.include_router(usuarios.router)
api_router.include_router(images.router)
api_router.include_router(subscriptions.router)
api_router.include_router(subscriptions.admin_router)

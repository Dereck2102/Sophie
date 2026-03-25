from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.api.deps import require_module_enabled, require_tenant_membership

from app.api.v1.endpoints import (
    admin,
    auth,
    boveda as credenciales,
    caja_chica,
    clientes,
    compras,
    configuracion,
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
tenant_api_router = APIRouter(prefix="/empresas/{empresa_id}", dependencies=[Depends(require_tenant_membership)])
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
api_router.include_router(usuarios.tenant_router)
api_router.include_router(configuracion.router)
api_router.include_router(images.router)
api_router.include_router(subscriptions.router)
api_router.include_router(subscriptions.admin_router)

# Tenant-prefixed aliases (B2B) for ERP modules.
# Legacy non-tenant routes remain available during migration.
tenant_api_router.include_router(
    dashboard.router,
    dependencies=[Depends(require_module_enabled("dashboard"))],
)
if settings.ENABLE_CRM_MODULE:
    tenant_api_router.include_router(
        clientes.router,
        dependencies=[Depends(require_module_enabled("clientes"))],
    )
tenant_api_router.include_router(
    ventas.router,
    dependencies=[Depends(require_module_enabled("ventas"))],
)
tenant_api_router.include_router(
    compras.router,
    dependencies=[Depends(require_module_enabled("compras"))],
)
tenant_api_router.include_router(
    inventario.router,
    dependencies=[Depends(require_module_enabled("inventario"))],
)
tenant_api_router.include_router(
    tickets.router,
    dependencies=[Depends(require_module_enabled("tickets"))],
)
tenant_api_router.include_router(
    proyectos.router,
    dependencies=[Depends(require_module_enabled("proyectos"))],
)
tenant_api_router.include_router(
    credenciales.router,
    dependencies=[Depends(require_module_enabled("configuracion"))],
)
if settings.ENABLE_CAJA_CHICA_MODULE:
    tenant_api_router.include_router(
        caja_chica.router,
        dependencies=[Depends(require_module_enabled("caja_chica"))],
    )
tenant_api_router.include_router(
    configuracion.router,
    dependencies=[Depends(require_module_enabled("configuracion"))],
)

api_router.include_router(tenant_api_router)

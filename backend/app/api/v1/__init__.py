from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    boveda,
    clientes,
    compras,
    dashboard,
    inventario,
    proyectos,
    tickets,
    usuarios,
    ventas,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(dashboard.router)
api_router.include_router(clientes.router)
api_router.include_router(ventas.router)
api_router.include_router(compras.router)
api_router.include_router(inventario.router)
api_router.include_router(tickets.router)
api_router.include_router(proyectos.router)
api_router.include_router(boveda.router)
api_router.include_router(usuarios.router)

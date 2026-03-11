from fastapi import APIRouter

from app.api.v1.endpoints import auth, clientes, ventas, inventario, tickets, boveda, usuarios

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(clientes.router)
api_router.include_router(ventas.router)
api_router.include_router(inventario.router)
api_router.include_router(tickets.router)
api_router.include_router(boveda.router)
api_router.include_router(usuarios.router)

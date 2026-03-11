from __future__ import annotations

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_clientes: int
    cotizaciones_mes: int
    tickets_abiertos: int
    productos_bajo_stock: int

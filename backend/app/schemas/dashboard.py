from __future__ import annotations

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_clientes: int
    cotizaciones_mes: int
    tickets_abiertos: int
    productos_bajo_stock: int
    revenue_mes: int
    proyectos_activos: int
    margen_bruto_mes: float = 0
    caja_chica_balance: float = 0
    caja_chica_egresos_mes: float = 0

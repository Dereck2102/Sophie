from __future__ import annotations

from typing import List, Optional

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


class DashboardTrendPoint(BaseModel):
    label: str
    ingresos: float
    compras: float
    caja_ingresos: float
    caja_egresos: float
    flujo_neto: float


class DashboardTopClient(BaseModel):
    id_cliente: int
    nombre: str
    total_facturado: float
    participacion_pct: float


class DashboardExpenseCategory(BaseModel):
    categoria: str
    total: float


class DashboardAlert(BaseModel):
    severity: str
    title: str
    detail: str
    link: Optional[str] = None


class DashboardReceivableBucket(BaseModel):
    bucket: str
    total: float
    cantidad: int


class DashboardReceivableDueItem(BaseModel):
    id_cotizacion: int
    numero: str
    id_cliente: int
    cliente_nombre: str
    estado: str
    total: float
    fecha_vencimiento: Optional[str] = None
    dias_para_vencer: Optional[int] = None
    dias_vencido: Optional[int] = None


class DashboardFinanceAnalytics(BaseModel):
    ingresos_facturados_mes: float
    compras_registradas_mes: float
    caja_ingresos_mes: float
    caja_egresos_mes: float
    flujo_neto_mes: float
    cuentas_por_cobrar: float
    ordenes_pendientes_monto: float
    margen_bruto_mes: float
    caja_chica_balance: float
    top_clientes: List[DashboardTopClient] = []
    egresos_por_categoria: List[DashboardExpenseCategory] = []
    cartera_aging: List[DashboardReceivableBucket] = []
    proximos_vencimientos: List[DashboardReceivableDueItem] = []
    tendencia_mensual: List[DashboardTrendPoint] = []
    alertas: List[DashboardAlert] = []

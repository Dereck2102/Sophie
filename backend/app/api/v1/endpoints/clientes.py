from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.infrastructure.models.auditoria import EventoCliente
from app.infrastructure.models.cliente import (
    Cliente,
    ClienteB2C,
    Empresa,
    TipoClienteEnum,
)
from app.infrastructure.models.proyectos import Proyecto
from app.infrastructure.models.tickets import Ticket
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.infrastructure.models.ventas import Cotizacion
from app.schemas.cliente import (
    ClienteCreate,
    ClienteOut,
    ClienteUpdate,
    EventoClienteOut,
)
from app.schemas.tickets import TicketOut
from app.schemas.ventas import CotizacionOut

router = APIRouter(prefix="/clientes", tags=["CRM - Clientes"])

_LOAD_OPTIONS = [
    selectinload(Cliente.empresa),
    selectinload(Cliente.cliente_b2c),
]


@router.get("/", response_model=List[ClienteOut])
async def list_clientes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    tipo: Optional[TipoClienteEnum] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[Cliente]:
    q = select(Cliente).options(*_LOAD_OPTIONS).offset(skip).limit(limit)
    if tipo:
        q = q.where(Cliente.tipo_cliente == tipo)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.post("/", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
async def create_cliente(
    body: ClienteCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.VENDEDOR, RolEnum.ADMIN))
    ],
) -> Cliente:
    cliente = Cliente(tipo_cliente=body.tipo_cliente, estado=body.estado)
    db.add(cliente)
    await db.flush()

    if body.tipo_cliente == TipoClienteEnum.B2B:
        if not body.empresa:
            raise HTTPException(status_code=400, detail="empresa data required for B2B client")
        db.add(Empresa(id_cliente=cliente.id_cliente, **body.empresa.model_dump()))
    else:
        if not body.cliente_b2c:
            raise HTTPException(
                status_code=400, detail="cliente_b2c data required for B2C client"
            )
        db.add(ClienteB2C(id_cliente=cliente.id_cliente, **body.cliente_b2c.model_dump()))

    db.add(
        EventoCliente(
            id_cliente=cliente.id_cliente,
            tipo_evento="ALTA",
            descripcion=f"Cliente {body.tipo_cliente.value} registrado.",
        )
    )
    await db.flush()
    await db.refresh(cliente, ["empresa", "cliente_b2c"])
    return cliente


@router.get("/{id_cliente}", response_model=ClienteOut)
async def get_cliente(
    id_cliente: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Cliente:
    result = await db.execute(
        select(Cliente).options(*_LOAD_OPTIONS).where(Cliente.id_cliente == id_cliente)
    )
    cliente = result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente not found")
    return cliente


@router.put("/{id_cliente}", response_model=ClienteOut)
async def update_cliente(
    id_cliente: int,
    body: ClienteUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.VENDEDOR, RolEnum.ADMIN))
    ],
) -> Cliente:
    result = await db.execute(
        select(Cliente).options(*_LOAD_OPTIONS).where(Cliente.id_cliente == id_cliente)
    )
    cliente = result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente not found")

    if body.estado:
        cliente.estado = body.estado

    if body.empresa and cliente.empresa:
        for k, v in body.empresa.model_dump(exclude_none=True).items():
            setattr(cliente.empresa, k, v)

    if body.cliente_b2c and cliente.cliente_b2c:
        for k, v in body.cliente_b2c.model_dump(exclude_none=True).items():
            setattr(cliente.cliente_b2c, k, v)

    await db.flush()
    await db.refresh(cliente, ["empresa", "cliente_b2c"])
    return cliente


@router.delete("/{id_cliente}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_cliente(
    id_cliente: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.ADMIN))],
) -> None:
    result = await db.execute(
        select(Cliente)
        .options(selectinload(Cliente.empresa), selectinload(Cliente.cliente_b2c), selectinload(Cliente.eventos))
        .where(Cliente.id_cliente == id_cliente)
    )
    cliente = result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente not found")

    tickets_count = await db.scalar(
        select(Ticket.id_ticket).where(Ticket.id_cliente == id_cliente).limit(1)
    )
    cotizacion_count = await db.scalar(
        select(Cotizacion.id_cotizacion).where(Cotizacion.id_cliente == id_cliente).limit(1)
    )
    proyecto_count = await db.scalar(
        select(Proyecto.id_proyecto).where(Proyecto.id_cliente == id_cliente).limit(1)
    )
    if tickets_count or cotizacion_count or proyecto_count:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar un cliente con tickets, cotizaciones o proyectos asociados. Desactívalo si ya tiene historial operativo.",
        )

    await db.delete(cliente)
    await db.flush()


@router.get("/{id_cliente}/timeline", response_model=List[EventoClienteOut])
async def get_cliente_timeline(
    id_cliente: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> list[EventoCliente]:
    result = await db.execute(
        select(EventoCliente)
        .where(EventoCliente.id_cliente == id_cliente)
        .order_by(EventoCliente.fecha.desc())
    )
    return list(result.scalars().all())


@router.get("/{id_cliente}/tickets", response_model=List[TicketOut])
async def get_cliente_tickets(
    id_cliente: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> list[Ticket]:
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id_cliente == id_cliente)
        .order_by(Ticket.fecha_creacion.desc())
    )
    return list(result.scalars().all())


@router.get("/{id_cliente}/cotizaciones", response_model=List[CotizacionOut])
async def get_cliente_cotizaciones(
    id_cliente: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> list[Cotizacion]:
    result = await db.execute(
        select(Cotizacion)
        .options(selectinload(Cotizacion.detalles))
        .where(Cotizacion.id_cliente == id_cliente)
        .order_by(Cotizacion.fecha_creacion.desc())
    )
    return list(result.scalars().all())


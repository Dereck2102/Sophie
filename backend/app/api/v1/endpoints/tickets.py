from __future__ import annotations

import base64
import json
import secrets
from datetime import datetime, timezone
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.infrastructure.models.auditoria import EventoCliente
from app.infrastructure.models.cliente import Cliente
from app.infrastructure.models.proyectos import Proyecto
from app.infrastructure.models.tickets import (
    IncidenciaIT,
    ReparacionTaller,
    RepuestoUsado,
    SLA,
    Ticket,
    TipoTicketEnum,
    EstadoTicketEnum,
)
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.schemas.tickets import (
    IncidenciaITOut,
    OrdenTrabajoPublicOut,
    ReparacionOut,
    ReparacionUpdate,
    RepuestoUsadoCreate,
    RepuestoUsadoOut,
    SLACreate,
    SLAOut,
    TicketCreate,
    TicketOut,
    TicketUpdate,
)

router = APIRouter(prefix="/tickets", tags=["Soporte Técnico"])

_VALID_ASSIGNEE_ROLES = {
    RolEnum.TECNICO_TALLER,
    RolEnum.TECNICO_IT,
    RolEnum.CONSULTOR_SENIOR,
    RolEnum.ADMIN,
}


def _next_ticket_numero(count: int) -> str:
    return f"TKT-{count + 1:06d}"


@router.get("/seguimiento/{token}", response_model=OrdenTrabajoPublicOut)
async def get_orden_by_token(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> OrdenTrabajoPublicOut:
    """Public endpoint – no authentication required. Used for client order tracking."""
    result = await db.execute(
        select(ReparacionTaller)
        .options(selectinload(ReparacionTaller.repuestos), selectinload(ReparacionTaller.ticket))
        .where(ReparacionTaller.token_seguimiento == token)
    )
    rep = result.scalar_one_or_none()
    if not rep or not rep.ticket:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada")

    t = rep.ticket
    return OrdenTrabajoPublicOut(
        ticket_numero=t.numero,
        ticket_titulo=t.titulo,
        ticket_descripcion=t.descripcion,
        ticket_estado=t.estado.value,
        ticket_prioridad=t.prioridad.value,
        ticket_fecha_creacion=t.fecha_creacion,
        ticket_fecha_inicio=t.fecha_inicio_trabajo,
        ticket_fecha_fin=t.fecha_fin_trabajo,
        equipo_descripcion=rep.equipo_descripcion,
        marca_equipo=rep.marca_equipo,
        modelo_equipo=rep.modelo_equipo,
        numero_serie_equipo=rep.numero_serie_equipo,
        accesorios_recibidos=rep.accesorios_recibidos,
        diagnostico=rep.diagnostico,
        costo_reparacion=float(rep.costo_reparacion) if rep.costo_reparacion else None,
        repuestos=rep.repuestos,
    )


@router.get("/", response_model=List[TicketOut])
async def list_tickets(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[Ticket]:
    query = select(Ticket).offset(skip).limit(limit).order_by(Ticket.fecha_creacion.desc())
    # Technicians only see their own assigned tickets
    if current_user.rol in (RolEnum.TECNICO_TALLER, RolEnum.TECNICO_IT):
        query = query.where(Ticket.id_tecnico == current_user.id_usuario)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/", response_model=TicketOut, status_code=201)
async def create_ticket(
    body: TicketCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Ticket:
    client_result = await db.execute(
        select(Cliente).where(Cliente.id_cliente == body.id_cliente)
    )
    cliente = client_result.scalar_one_or_none()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente not found")

    if body.id_tecnico is not None:
        user_result = await db.execute(
            select(Usuario).where(Usuario.id_usuario == body.id_tecnico)
        )
        tecnico = user_result.scalar_one_or_none()
        if not tecnico or tecnico.rol not in _VALID_ASSIGNEE_ROLES:
            raise HTTPException(
                status_code=400,
                detail="Solo se pueden asignar técnicos o encargados válidos",
            )

    if body.id_proyecto is not None:
        proyecto_result = await db.execute(
            select(Proyecto).where(Proyecto.id_proyecto == body.id_proyecto)
        )
        proyecto = proyecto_result.scalar_one_or_none()
        if not proyecto:
            raise HTTPException(status_code=404, detail="Proyecto not found")
        if proyecto.id_cliente != body.id_cliente:
            raise HTTPException(
                status_code=400,
                detail="El proyecto seleccionado no pertenece al cliente del ticket",
            )

    count_result = await db.execute(select(func.count(Ticket.id_ticket)))
    count = count_result.scalar_one() or 0
    numero = _next_ticket_numero(count)

    ticket_data = body.model_dump(exclude={
        "equipo_descripcion", "marca_equipo", "modelo_equipo",
        "numero_serie_equipo", "accesorios_recibidos", "email_cliente",
    })
    ticket = Ticket(numero=numero, **ticket_data)
    db.add(ticket)
    await db.flush()

    if body.tipo == TipoTicketEnum.REPARACION:
        token = secrets.token_urlsafe(32)
        db.add(ReparacionTaller(
            id_ticket=ticket.id_ticket,
            equipo_descripcion=body.equipo_descripcion,
            marca_equipo=body.marca_equipo,
            modelo_equipo=body.modelo_equipo,
            numero_serie_equipo=body.numero_serie_equipo,
            accesorios_recibidos=body.accesorios_recibidos,
            email_cliente=body.email_cliente,
            token_seguimiento=token,
        ))
    else:
        # Try to find applicable SLA
        sla_result = await db.execute(select(SLA).limit(1))
        sla = sla_result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        fecha_limite_r = None
        fecha_limite_res = None
        if sla:
            from datetime import timedelta

            fecha_limite_r = now + timedelta(hours=sla.tiempo_respuesta_horas)
            fecha_limite_res = now + timedelta(hours=sla.tiempo_resolucion_horas)

        db.add(
            IncidenciaIT(
                id_ticket=ticket.id_ticket,
                id_sla=sla.id_sla if sla else None,
                fecha_limite_respuesta=fecha_limite_r,
                fecha_limite_resolucion=fecha_limite_res,
            )
        )

    db.add(
        EventoCliente(
            id_cliente=body.id_cliente,
            tipo_evento="TICKET",
            descripcion=f"Ticket {numero} creado.",
        )
    )
    await db.flush()
    return ticket


@router.get("/{id_ticket}", response_model=TicketOut)
async def get_ticket(
    id_ticket: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Ticket:
    result = await db.execute(select(Ticket).where(Ticket.id_ticket == id_ticket))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/{id_ticket}", response_model=TicketOut)
async def update_ticket(
    id_ticket: int,
    body: TicketUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Ticket:
    result = await db.execute(select(Ticket).where(Ticket.id_ticket == id_ticket))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(ticket, k, v)
    if body.estado and body.estado.value in ("resuelto", "cerrado"):
        ticket.fecha_cierre = datetime.now(timezone.utc)
    await db.flush()
    return ticket


@router.delete("/{id_ticket}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    id_ticket: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.ADMIN))],
) -> None:
    result = await db.execute(select(Ticket).where(Ticket.id_ticket == id_ticket))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    await db.delete(ticket)
    await db.flush()


def _assert_ticket_assignee(ticket: Ticket, current_user: Usuario) -> None:
    """Raise 403 if current_user is not the assigned technician (admins are exempt)."""
    if ticket.id_tecnico != current_user.id_usuario and current_user.rol != RolEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Not assigned to this ticket")


@router.post("/{id_ticket}/start", response_model=TicketOut)
async def start_ticket(
    id_ticket: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Ticket:
    """Mark a ticket as started (sets fecha_inicio_trabajo and status to en_progreso)."""
    result = await db.execute(select(Ticket).where(Ticket.id_ticket == id_ticket))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    _assert_ticket_assignee(ticket, current_user)
    ticket.fecha_inicio_trabajo = datetime.now(timezone.utc)
    ticket.estado = EstadoTicketEnum.EN_PROGRESO
    await db.flush()
    return ticket


@router.post("/{id_ticket}/finish", response_model=TicketOut)
async def finish_ticket(
    id_ticket: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Ticket:
    """Mark a ticket as finished (sets fecha_fin_trabajo and status to resuelto)."""
    result = await db.execute(select(Ticket).where(Ticket.id_ticket == id_ticket))
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    _assert_ticket_assignee(ticket, current_user)
    ticket.fecha_fin_trabajo = datetime.now(timezone.utc)
    ticket.estado = EstadoTicketEnum.RESUELTO
    ticket.fecha_cierre = datetime.now(timezone.utc)
    await db.flush()
    return ticket


@router.get("/{id_ticket}/reparacion", response_model=ReparacionOut)
async def get_reparacion(
    id_ticket: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.TECNICO_TALLER, RolEnum.ADMIN))
    ],
) -> ReparacionTaller:
    result = await db.execute(
        select(ReparacionTaller)
        .options(selectinload(ReparacionTaller.repuestos))
        .where(ReparacionTaller.id_ticket == id_ticket)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Reparacion not found")
    return r


@router.patch("/{id_ticket}/reparacion", response_model=ReparacionOut)
async def update_reparacion(
    id_ticket: int,
    body: ReparacionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.TECNICO_TALLER, RolEnum.ADMIN))
    ],
) -> ReparacionTaller:
    result = await db.execute(
        select(ReparacionTaller)
        .options(selectinload(ReparacionTaller.repuestos))
        .where(ReparacionTaller.id_ticket == id_ticket)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Reparacion not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(r, k, v)
    await db.flush()
    await db.refresh(r, ["repuestos"])
    return r


@router.post("/{id_ticket}/reparacion/fotos", response_model=ReparacionOut)
async def upload_fotos(
    id_ticket: int,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(
        require_roles(RolEnum.TECNICO_TALLER, RolEnum.ADMIN)
    ),
) -> ReparacionTaller:
    if len(files) < 1:
        raise HTTPException(status_code=400, detail="At least 1 file required")
    result = await db.execute(
        select(ReparacionTaller)
        .options(selectinload(ReparacionTaller.repuestos))
        .where(ReparacionTaller.id_ticket == id_ticket)
    )
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Reparacion not found")

    existing: list[str] = json.loads(r.fotos_urls or "[]")
    for f in files:
        content = await f.read()
        b64 = base64.b64encode(content).decode()
        mime = f.content_type or "image/jpeg"
        existing.append(f"data:{mime};base64,{b64}")
    r.fotos_urls = json.dumps(existing)
    await db.flush()
    await db.refresh(r, ["repuestos"])
    return r


@router.post("/{id_ticket}/reparacion/repuestos", response_model=RepuestoUsadoOut)
async def add_repuesto(
    id_ticket: int,
    body: RepuestoUsadoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.TECNICO_TALLER, RolEnum.ADMIN))
    ],
) -> RepuestoUsado:
    repuesto = RepuestoUsado(id_ticket=id_ticket, **body.model_dump())
    db.add(repuesto)
    await db.flush()
    return repuesto


@router.get("/{id_ticket}/incidencia", response_model=IncidenciaITOut)
async def get_incidencia(
    id_ticket: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.TECNICO_IT, RolEnum.ADMIN))
    ],
) -> IncidenciaIT:
    result = await db.execute(
        select(IncidenciaIT).where(IncidenciaIT.id_ticket == id_ticket)
    )
    inc = result.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="IncidenciaIT not found")
    return inc


@router.get("/sla/", response_model=List[SLAOut])
async def list_slas(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario, Depends(require_roles(RolEnum.TECNICO_IT, RolEnum.ADMIN))
    ],
) -> list[SLA]:
    result = await db.execute(select(SLA))
    return list(result.scalars().all())


@router.post("/sla/", response_model=SLAOut, status_code=201)
async def create_sla(
    body: SLACreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.ADMIN))],
) -> SLA:
    sla = SLA(**body.model_dump())
    db.add(sla)
    await db.flush()
    return sla

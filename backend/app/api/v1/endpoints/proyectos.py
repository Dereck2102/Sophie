from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.infrastructure.models.proyectos import (
    MiembroProyecto,
    Proyecto,
    RegistroTiempo,
    Tarea,
)
from app.infrastructure.models.sistema import ConfiguracionSistema
from app.infrastructure.models.tickets import EstadoTicketEnum, RepuestoUsado, ReparacionTaller, Ticket
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.infrastructure.models.ventas import Cotizacion, EstadoCotizacionEnum, Venta
from app.schemas.proyectos import (
    CotizacionProyectoOut,
    MiembroCreate,
    MiembroOut,
    ProyectoCreate,
    ProyectoEstadisticasOut,
    ProyectoRentabilidadOut,
    ProyectoOut,
    ProyectoUpdate,
    RegistroTiempoCreate,
    RegistroTiempoOut,
    TareaCreate,
    TareaOut,
    TareaUpdate,
)

router = APIRouter(prefix="/proyectos", tags=["Proyectos & Asesoría"])


@router.get("/", response_model=List[ProyectoOut])
async def list_proyectos(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[Proyecto]:
    result = await db.execute(
        select(Proyecto)
        .offset(skip)
        .limit(limit)
        .order_by(Proyecto.fecha_creacion.desc())
    )
    return list(result.scalars().all())


@router.post("/", response_model=ProyectoOut, status_code=status.HTTP_201_CREATED)
async def create_proyecto(
    body: ProyectoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario,
        Depends(
            require_roles(
                RolEnum.EJECUTIVO,
                RolEnum.EJECUTIVO,
                RolEnum.SUPERADMIN,
            )
        ),
    ],
) -> Proyecto:
    proyecto = Proyecto(**body.model_dump())
    db.add(proyecto)
    await db.flush()
    return proyecto


@router.get("/{id_proyecto}", response_model=ProyectoOut)
async def get_proyecto(
    id_proyecto: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Proyecto:
    result = await db.execute(
        select(Proyecto).where(Proyecto.id_proyecto == id_proyecto)
    )
    proyecto = result.scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto not found")
    return proyecto


@router.patch("/{id_proyecto}", response_model=ProyectoOut)
async def update_proyecto(
    id_proyecto: int,
    body: ProyectoUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario,
        Depends(
            require_roles(
                RolEnum.EJECUTIVO,
                RolEnum.EJECUTIVO,
                RolEnum.SUPERADMIN,
            )
        ),
    ],
) -> Proyecto:
    result = await db.execute(
        select(Proyecto).where(Proyecto.id_proyecto == id_proyecto)
    )
    proyecto = result.scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(proyecto, k, v)
    await db.flush()
    return proyecto


@router.delete("/{id_proyecto}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_proyecto(
    id_proyecto: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario,
        Depends(
            require_roles(
                RolEnum.EJECUTIVO,
                RolEnum.EJECUTIVO,
                RolEnum.SUPERADMIN,
            )
        ),
    ],
) -> None:
    result = await db.execute(
        select(Proyecto).where(Proyecto.id_proyecto == id_proyecto)
    )
    proyecto = result.scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto not found")
    await db.delete(proyecto)
    await db.flush()


# ── Tareas ──────────────────────────────────────────────────────────────────


@router.get("/{id_proyecto}/tareas", response_model=List[TareaOut])
async def list_tareas(
    id_proyecto: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> list[Tarea]:
    result = await db.execute(
        select(Tarea)
        .where(Tarea.id_proyecto == id_proyecto)
        .order_by(Tarea.fecha_creacion)
    )
    return list(result.scalars().all())


@router.post("/{id_proyecto}/tareas", response_model=TareaOut, status_code=201)
async def create_tarea(
    id_proyecto: int,
    body: TareaCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Tarea:
    # Verify project exists
    result = await db.execute(
        select(Proyecto).where(Proyecto.id_proyecto == id_proyecto)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Proyecto not found")

    if body.id_asignado is not None:
        miembro_result = await db.execute(
            select(MiembroProyecto).where(
                MiembroProyecto.id_proyecto == id_proyecto,
                MiembroProyecto.id_usuario == body.id_asignado,
            )
        )
        if not miembro_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Assigned user is not a project member")

    tarea = Tarea(id_proyecto=id_proyecto, **body.model_dump(exclude={"id_proyecto"}))
    db.add(tarea)
    await db.flush()
    return tarea


@router.patch("/tareas/{id_tarea}", response_model=TareaOut)
async def update_tarea(
    id_tarea: int,
    body: TareaUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Tarea:
    result = await db.execute(select(Tarea).where(Tarea.id_tarea == id_tarea))
    tarea = result.scalar_one_or_none()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea not found")

    if body.id_asignado is not None:
        miembro_result = await db.execute(
            select(MiembroProyecto).where(
                MiembroProyecto.id_proyecto == tarea.id_proyecto,
                MiembroProyecto.id_usuario == body.id_asignado,
            )
        )
        if not miembro_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Assigned user is not a project member")

    for k, v in body.model_dump(exclude_none=True).items():
        setattr(tarea, k, v)
    await db.flush()
    return tarea


@router.delete("/tareas/{id_tarea}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete_tarea(
    id_tarea: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> None:
    result = await db.execute(select(Tarea).where(Tarea.id_tarea == id_tarea))
    tarea = result.scalar_one_or_none()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea not found")
    await db.delete(tarea)
    await db.flush()


# ── Registros de Tiempo ──────────────────────────────────────────────────────


@router.post("/tareas/{id_tarea}/tiempo", response_model=RegistroTiempoOut, status_code=201)
async def log_tiempo(
    id_tarea: int,
    body: RegistroTiempoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> RegistroTiempo:
    result = await db.execute(select(Tarea).where(Tarea.id_tarea == id_tarea))
    tarea = result.scalar_one_or_none()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea not found")

    registro = RegistroTiempo(
        id_tarea=id_tarea,
        id_usuario=current_user.id_usuario,
        horas=body.horas,
        descripcion=body.descripcion,
    )
    db.add(registro)
    tarea.horas_reales = float(tarea.horas_reales or 0) + body.horas
    await db.flush()
    return registro


# ── Miembros ─────────────────────────────────────────────────────────────────


@router.get("/{id_proyecto}/miembros", response_model=List[MiembroOut])
async def list_miembros(
    id_proyecto: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> list[MiembroProyecto]:
    result = await db.execute(
        select(MiembroProyecto).where(MiembroProyecto.id_proyecto == id_proyecto)
    )
    return list(result.scalars().all())


@router.post("/{id_proyecto}/miembros", response_model=MiembroOut, status_code=201)
async def add_miembro(
    id_proyecto: int,
    body: MiembroCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[
        Usuario,
        Depends(require_roles(RolEnum.EJECUTIVO, RolEnum.EJECUTIVO, RolEnum.SUPERADMIN)),
    ],
) -> MiembroProyecto:
    miembro = MiembroProyecto(
        id_proyecto=id_proyecto,
        id_usuario=body.id_usuario,
        rol_en_proyecto=body.rol_en_proyecto,
    )
    db.add(miembro)
    await db.flush()
    return miembro


@router.get("/{id_proyecto}/cotizaciones", response_model=List[CotizacionProyectoOut])
async def list_cotizaciones_proyecto(
    id_proyecto: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    limit: int = Query(30, ge=1, le=200),
) -> list[CotizacionProyectoOut]:
    proyecto_result = await db.execute(
        select(Proyecto.id_proyecto).where(Proyecto.id_proyecto == id_proyecto)
    )
    if not proyecto_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Proyecto not found")

    result = await db.execute(
        select(Cotizacion, Venta.numero_factura, Venta.fecha_factura)
        .outerjoin(Venta, Venta.id_cotizacion == Cotizacion.id_cotizacion)
        .where(Cotizacion.id_proyecto == id_proyecto)
        .order_by(Cotizacion.fecha_creacion.desc())
        .limit(limit)
    )

    rows = result.all()
    return [
        CotizacionProyectoOut(
            id_cotizacion=cot.id_cotizacion,
            numero=cot.numero,
            estado=cot.estado.value,
            total=float(cot.total or 0),
            fecha_creacion=cot.fecha_creacion,
            numero_factura=numero_factura,
            fecha_factura=fecha_factura,
        )
        for cot, numero_factura, fecha_factura in rows
    ]


@router.get("/{id_proyecto}/rentabilidad", response_model=ProyectoRentabilidadOut)
async def get_proyecto_rentabilidad(
    id_proyecto: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> ProyectoRentabilidadOut:
    proyecto_result = await db.execute(
        select(Proyecto).where(Proyecto.id_proyecto == id_proyecto)
    )
    proyecto = proyecto_result.scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto not found")

    horas_result = await db.execute(
        select(func.coalesce(func.sum(Tarea.horas_reales), 0)).where(Tarea.id_proyecto == id_proyecto)
    )
    horas_reales = float(horas_result.scalar_one() or 0)

    costo_hora_result = await db.execute(
        select(ConfiguracionSistema.costo_hora_tecnica_default).where(ConfiguracionSistema.id_configuracion == 1)
    )
    costo_hora = float(costo_hora_result.scalar_one_or_none() or 25)
    costo_horas_tecnicas = round(horas_reales * costo_hora, 2)

    reparaciones_result = await db.execute(
        select(func.coalesce(func.sum(ReparacionTaller.costo_reparacion), 0))
        .join(Ticket, Ticket.id_ticket == ReparacionTaller.id_ticket)
        .where(Ticket.id_proyecto == id_proyecto)
    )
    costo_reparaciones = float(reparaciones_result.scalar_one() or 0)

    repuestos_result = await db.execute(
        select(func.coalesce(func.sum(RepuestoUsado.cantidad * RepuestoUsado.precio_unitario), 0))
        .join(Ticket, Ticket.id_ticket == RepuestoUsado.id_ticket)
        .where(Ticket.id_proyecto == id_proyecto)
    )
    costo_repuestos = float(repuestos_result.scalar_one() or 0)

    tickets_total_result = await db.execute(
        select(func.count(Ticket.id_ticket)).where(Ticket.id_proyecto == id_proyecto)
    )
    tickets_total = int(tickets_total_result.scalar_one() or 0)

    tickets_cerrados_result = await db.execute(
        select(func.count(Ticket.id_ticket)).where(
            Ticket.id_proyecto == id_proyecto,
            Ticket.estado.in_([EstadoTicketEnum.RESUELTO, EstadoTicketEnum.CERRADO]),
        )
    )
    tickets_cerrados = int(tickets_cerrados_result.scalar_one() or 0)

    ingresos_result = await db.execute(
        select(func.coalesce(func.sum(Cotizacion.total), 0)).where(
            Cotizacion.id_proyecto == id_proyecto,
            Cotizacion.estado == EstadoCotizacionEnum.FACTURADA,
        )
    )
    ingresos_facturados = float(ingresos_result.scalar_one() or 0)

    presupuesto = float(proyecto.presupuesto or 0)
    costo_total_operativo = round(costo_horas_tecnicas + costo_reparaciones + costo_repuestos, 2)
    margen_presupuestario = round(presupuesto - costo_total_operativo, 2)
    utilidad_neta_real = round(ingresos_facturados - costo_total_operativo, 2)
    margen_neto_pct = round((utilidad_neta_real / ingresos_facturados) * 100, 2) if ingresos_facturados > 0 else 0
    consumo_presupuesto_pct = round((costo_total_operativo / presupuesto) * 100, 2) if presupuesto > 0 else 0

    return ProyectoRentabilidadOut(
        id_proyecto=id_proyecto,
        presupuesto=round(presupuesto, 2),
        ingresos_facturados=round(ingresos_facturados, 2),
        costo_horas_tecnicas=round(costo_horas_tecnicas, 2),
        costo_reparaciones=round(costo_reparaciones, 2),
        costo_repuestos=round(costo_repuestos, 2),
        costo_total_operativo=costo_total_operativo,
        margen_presupuestario=margen_presupuestario,
        utilidad_neta_real=utilidad_neta_real,
        margen_neto_pct=margen_neto_pct,
        consumo_presupuesto_pct=consumo_presupuesto_pct,
        tickets_total=tickets_total,
        tickets_cerrados=tickets_cerrados,
    )


@router.get("/{id_proyecto}/estadisticas", response_model=ProyectoEstadisticasOut)
async def get_proyecto_estadisticas(
    id_proyecto: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> ProyectoEstadisticasOut:
    proyecto_result = await db.execute(select(Proyecto).where(Proyecto.id_proyecto == id_proyecto))
    proyecto = proyecto_result.scalar_one_or_none()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto not found")

    total_tareas_result = await db.execute(select(func.count(Tarea.id_tarea)).where(Tarea.id_proyecto == id_proyecto))
    tareas_completadas_result = await db.execute(
        select(func.count(Tarea.id_tarea)).where(Tarea.id_proyecto == id_proyecto, Tarea.estado == "completado")
    )
    tareas_pendientes_result = await db.execute(
        select(func.count(Tarea.id_tarea)).where(Tarea.id_proyecto == id_proyecto, Tarea.estado == "pendiente")
    )
    tareas_en_progreso_result = await db.execute(
        select(func.count(Tarea.id_tarea)).where(Tarea.id_proyecto == id_proyecto, Tarea.estado == "en_progreso")
    )

    horas_estimadas_result = await db.execute(
        select(func.coalesce(func.sum(Tarea.horas_estimadas), 0)).where(Tarea.id_proyecto == id_proyecto)
    )
    horas_realizadas_result = await db.execute(
        select(func.coalesce(func.sum(Tarea.horas_reales), 0)).where(Tarea.id_proyecto == id_proyecto)
    )
    miembros_result = await db.execute(
        select(func.count(MiembroProyecto.id_miembro)).where(MiembroProyecto.id_proyecto == id_proyecto)
    )
    tickets_result = await db.execute(select(func.count(Ticket.id_ticket)).where(Ticket.id_proyecto == id_proyecto))
    ingresos_result = await db.execute(
        select(func.coalesce(func.sum(Cotizacion.total), 0)).where(
            Cotizacion.id_proyecto == id_proyecto,
            Cotizacion.estado == EstadoCotizacionEnum.FACTURADA,
        )
    )

    total_tareas = int(total_tareas_result.scalar_one() or 0)
    tareas_completadas = int(tareas_completadas_result.scalar_one() or 0)
    tareas_pendientes = int(tareas_pendientes_result.scalar_one() or 0)
    tareas_en_progreso = int(tareas_en_progreso_result.scalar_one() or 0)
    horas_estimadas = float(horas_estimadas_result.scalar_one() or 0)
    horas_realizadas = float(horas_realizadas_result.scalar_one() or 0)
    miembros_asignados = int(miembros_result.scalar_one() or 0)
    tickets_asociados = int(tickets_result.scalar_one() or 0)
    ingresos_facturados = float(ingresos_result.scalar_one() or 0)
    presupuesto = float(proyecto.presupuesto) if proyecto.presupuesto is not None else None

    porcentaje_completacion = round((tareas_completadas / total_tareas) * 100, 2) if total_tareas > 0 else 0
    variancia_horas_pct = round(((horas_realizadas - horas_estimadas) / horas_estimadas) * 100, 2) if horas_estimadas > 0 else 0
    margen_neto_pct = (
        round(((ingresos_facturados - presupuesto) / ingresos_facturados) * 100, 2)
        if ingresos_facturados > 0 and presupuesto is not None
        else 0
    )

    dias_restantes = None
    if proyecto.fecha_fin is not None:
        fecha_fin = proyecto.fecha_fin
        if fecha_fin.tzinfo is None:
            fecha_fin = fecha_fin.replace(tzinfo=UTC)
        dias_restantes = max((fecha_fin - datetime.now(UTC)).days, 0)

    return ProyectoEstadisticasOut(
        id_proyecto=proyecto.id_proyecto,
        nombre=proyecto.nombre,
        estado=proyecto.estado.value,
        total_tareas=total_tareas,
        tareas_completadas=tareas_completadas,
        tareas_pendientes=tareas_pendientes,
        tareas_en_progreso=tareas_en_progreso,
        porcentaje_completacion=porcentaje_completacion,
        tickets_asociados=tickets_asociados,
        horas_estimadas=round(horas_estimadas, 2),
        horas_realizadas=round(horas_realizadas, 2),
        variancia_horas_pct=variancia_horas_pct,
        miembros_asignados=miembros_asignados,
        presupuesto=round(presupuesto, 2) if presupuesto is not None else None,
        ingresos_facturados=round(ingresos_facturados, 2),
        margen_neto_pct=margen_neto_pct,
        fecha_inicio=proyecto.fecha_inicio,
        fecha_fin=proyecto.fecha_fin,
        dias_restantes=dias_restantes,
    )

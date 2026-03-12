from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.infrastructure.models.proyectos import (
    MiembroProyecto,
    Proyecto,
    RegistroTiempo,
    Tarea,
)
from app.infrastructure.models.usuario import RolEnum, Usuario
from app.schemas.proyectos import (
    MiembroCreate,
    MiembroOut,
    ProyectoCreate,
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
                RolEnum.DESARROLLADOR,
                RolEnum.CONSULTOR_SENIOR,
                RolEnum.ADMIN,
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
                RolEnum.DESARROLLADOR,
                RolEnum.CONSULTOR_SENIOR,
                RolEnum.ADMIN,
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
    current_user: Annotated[Usuario, Depends(require_roles(RolEnum.ADMIN))],
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
        Depends(require_roles(RolEnum.DESARROLLADOR, RolEnum.CONSULTOR_SENIOR, RolEnum.ADMIN)),
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

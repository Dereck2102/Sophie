from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.infrastructure.models.usuario import Usuario
from app.schemas.configuracion import (
    ConfiguracionEmpresaResponse,
    ConfiguracionEmpresaUpdate,
    ConfiguracionUsuarioResponse,
    ConfiguracionUsuarioUpdate,
)

router = APIRouter(prefix="/api/v1/configuracion", tags=["configuracion"])


# =============== ENDPOINTS DE CONFIGURACIÓN DE EMPRESA ===============

@router.get("/empresa/{id_cliente}", response_model=ConfiguracionEmpresaResponse)
async def get_empresa_config(
    id_cliente: int,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConfiguracionEmpresaResponse:
    """Obtener configuración de una empresa (solo admin o superadmin de esa empresa)"""
    # Validar que el usuario sea admin/super de esa empresa o superadmin global
    if current_user.rol != 'superadmin' and current_user.id_cliente != id_cliente:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para esta empresa")
    
    q = await db.execute(
        "SELECT * FROM configuracion_empresa WHERE id_cliente = :id_cliente",
        {"id_cliente": id_cliente}
    )
    config = q.fetchone()
    
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuración no encontrada")
    
    return ConfiguracionEmpresaResponse(**dict(config))


@router.patch("/empresa/{id_cliente}", response_model=ConfiguracionEmpresaResponse)
async def update_empresa_config(
    id_cliente: int,
    data: ConfiguracionEmpresaUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConfiguracionEmpresaResponse:
    """Actualizar configuración de una empresa (solo admin o superadmin)"""
    # Validar que el usuario sea admin/super de esa empresa o superadmin global
    if current_user.rol != 'superadmin' and current_user.id_cliente != id_cliente:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para esta empresa")
    
    if current_user.rol not in ('admin', 'superadmin'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administradores pueden editar configuración")
    
    # Obtener config actual
    stmt = "SELECT * FROM configuracion_empresa WHERE id_cliente = :id_cliente"
    result = await db.execute(stmt, {"id_cliente": id_cliente})
    config = result.fetchone()
    
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuración no encontrada")
    
    # Actualizar solo campos no nulos
    update_data = data.dict(exclude_unset=True)
    stmt = "UPDATE configuracion_empresa SET "
    values = {}
    
    for i, (key, value) in enumerate(update_data.items()):
        if i > 0:
            stmt += ", "
        stmt += f"{key} = :{key}"
        values[key] = value
    
    stmt += " WHERE id_cliente = :id_cliente RETURNING *"
    values['id_cliente'] = id_cliente
    
    result = await db.execute(stmt, values)
    updated = result.fetchone()
    await db.commit()
    
    return ConfiguracionEmpresaResponse(**dict(updated))


# =============== ENDPOINTS DE CONFIGURACIÓN DE USUARIO ===============

@router.get("/usuario/mio", response_model=ConfiguracionUsuarioResponse)
async def get_my_user_config(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConfiguracionUsuarioResponse:
    """Obtener mi configuración personal"""
    query = "SELECT * FROM configuracion_usuario WHERE id_usuario = :id_usuario"
    result = await db.execute(query, {"id_usuario": current_user.id_usuario})
    config = result.fetchone()
    
    if not config:
        # Crear configuración por defecto
        insert_query = """
        INSERT INTO configuracion_usuario (id_usuario, preferencia_idioma, tema, notificaciones_email, notificaciones_sms)
        VALUES (:id_usuario, 'es', 'system', true, false)
        RETURNING *
        """
        result = await db.execute(insert_query, {"id_usuario": current_user.id_usuario})
        await db.commit()
        config = result.fetchone()
    
    return ConfiguracionUsuarioResponse(**dict(config))


@router.patch("/usuario/mio", response_model=ConfiguracionUsuarioResponse)
async def update_my_user_config(
    data: ConfiguracionUsuarioUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConfiguracionUsuarioResponse:
    """Actualizar mi configuración personal"""
    update_data = data.dict(exclude_unset=True)
    
    if not update_data:
        # Si no hay cambios, devolver configuración actual
        query = "SELECT * FROM configuracion_usuario WHERE id_usuario = :id_usuario"
        result = await db.execute(query, {"id_usuario": current_user.id_usuario})
        config = result.fetchone()
        return ConfiguracionUsuarioResponse(**dict(config))
    
    # Construir query de actualización dinámica
    stmt = "UPDATE configuracion_usuario SET "
    values = {}
    
    for i, (key, value) in enumerate(update_data.items()):
        if i > 0:
            stmt += ", "
        stmt += f"{key} = :{key}"
        values[key] = value
    
    stmt += " WHERE id_usuario = :id_usuario RETURNING *"
    values['id_usuario'] = current_user.id_usuario
    
    result = await db.execute(stmt, values)
    updated = result.fetchone()
    
    if not updated:
        # Si no existe, crear nueva
        insert_query = """
        INSERT INTO configuracion_usuario (id_usuario, preferencia_idioma, tema, notificaciones_email, notificaciones_sms)
        VALUES (:id_usuario, 'es', 'system', true, false)
        RETURNING *
        """
        result = await db.execute(insert_query, {"id_usuario": current_user.id_usuario})
        updated = result.fetchone()
    
    await db.commit()
    return ConfiguracionUsuarioResponse(**dict(updated))


# =============== ENDPOINTS AUXILIARES ===============

@router.get("/suscripcion/mi-tipo")
async def get_my_subscription_type(
    current_user: Usuario = Depends(get_current_user),
) -> dict:
    """Obtener tipo de suscripción del usuario actual (individual/corporativa)"""
    return {
        "tipo_suscripcion": current_user.tipo_suscripcion or "corporativa",
        "id_cliente": current_user.id_cliente,
        "id_empresa": current_user.id_empresa,
        "es_admin_global": current_user.es_admin_global or False,
    }

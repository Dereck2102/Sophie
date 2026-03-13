"""
Endpoint para procesamiento y optimización de imágenes.

Provee:
- Upload y optimización automática
- Inferencia de tipo por context
- Información de imagen
"""

from __future__ import annotations

import base64
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.infrastructure.models.usuario import Usuario
from app.services.image_service import ImageOptimizationError, get_image_info, optimize_image

router = APIRouter(prefix="/images", tags=["Imágenes"])


class ImageUploadOut:
    pass


@router.post("/optimize")
async def optimize_image_endpoint(
    file: UploadFile = File(...),
    image_type: str = "default",
    target_width: Optional[int] = None,
    current_user: Usuario = Depends(get_current_user),
) -> dict:
    """
    Sube y optimiza una imagen. Retorna el data URL optimizado.
    
    - **file**: Archivo de imagen (JPG, PNG, WebP)
    - **image_type**: Tipo de optimización (profile, document, gallery, default)
    - **target_width**: Ancho máximo en píxeles (opcional)
    """
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se aceptan imágenes. Tipo recibido: {file.content_type}",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío",
        )

    mime = file.content_type or "image/jpeg"
    raw_url = f"data:{mime};base64,{base64.b64encode(content).decode()}"

    try:
        optimized_url = optimize_image(raw_url, image_type=image_type, target_width=target_width)
        info = get_image_info(optimized_url)
    except ImageOptimizationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No se pudo procesar la imagen: {e}",
        )

    original_size = len(content)
    savings_pct = round((1 - info["size_bytes"] / original_size) * 100, 1) if original_size > 0 else 0

    return {
        "data_url": optimized_url,
        "original_size_kb": round(original_size / 1024, 2),
        "optimized_size_kb": info["size_kb"],
        "size_reduction_pct": savings_pct,
        "format": info.get("format"),
        "dimensions": {"width": info["width"], "height": info["height"]},
    }


@router.post("/optimize-base64")
async def optimize_base64_endpoint(
    data_url: str,
    image_type: str = "default",
    target_width: Optional[int] = None,
    current_user: Annotated[Usuario, Depends(get_current_user)] = None,
) -> dict:
    """
    Optimiza una imagen enviada como data URL (base64).
    Útil para imágenes capturadas desde el browser.
    """
    if not data_url.startswith("data:image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen debe ser un data URL válido (data:image/...)",
        )

    try:
        info_before = get_image_info(data_url)
        optimized_url = optimize_image(data_url, image_type=image_type, target_width=target_width)
        info_after = get_image_info(optimized_url)
    except ImageOptimizationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No se pudo procesar la imagen: {e}",
        )

    savings_pct = round((1 - info_after["size_bytes"] / info_before["size_bytes"]) * 100, 1) if info_before["size_bytes"] > 0 else 0

    return {
        "data_url": optimized_url,
        "original_size_kb": info_before["size_kb"],
        "optimized_size_kb": info_after["size_kb"],
        "size_reduction_pct": savings_pct,
        "format": info_after.get("format"),
        "dimensions": {"width": info_after["width"], "height": info_after["height"]},
    }


@router.post("/info")
async def get_image_info_endpoint(
    file: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
) -> dict:
    """Retorna información de una imagen sin modificarla."""
    content = await file.read()
    mime = file.content_type or "image/jpeg"
    raw_url = f"data:{mime};base64,{base64.b64encode(content).decode()}"

    try:
        info = get_image_info(raw_url)
    except ImageOptimizationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return info

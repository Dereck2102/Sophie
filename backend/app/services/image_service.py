"""
Servicio de procesamiento y optimización de imágenes.

Maneja:
- Validación de formatos y tamaños
- Optimización automática con límites de peso
- Almacenamiento en base64 o filesystem
"""

import base64
import io
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image

# Límites de tamaño por tipo de imagen (bytes)
IMAGE_LIMITS = {
    "profile": 350_000,      # 350 KB para fotos de perfil
    "document": 2_000_000,   # 2 MB para documentos
    "gallery": 1_000_000,    # 1 MB para galerías
    "default": 1_500_000,    # 1.5 MB por defecto
}

# Calidades de compresión según tipo
COMPRESSION_QUALITY = {
    "profile": 80,      # Equilibrio calidad/peso para perfiles
    "document": 90,     # Muy alta para documentos
    "gallery": 75,      # Calidad media para galerías
    "default": 80,
}

# Formatos permitidos
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

# Directorio de almacenamiento
STORAGE_DIR = Path("/app/storage/uploads")


class ImageOptimizationError(Exception):
    """Error en procesamiento de imagen."""
    pass


def validate_data_url(data_url: str) -> tuple[str, bytes]:
    """
    Valida y parsea una data URL de imagen.
    
    Args:
        data_url: Data URL en formato "data:image/png;base64,..."
        
    Returns:
        Tupla (mime_type, datos_binarios)
        
    Raises:
        ImageOptimizationError: Si la data URL es inválida
    """
    if not data_url.startswith("data:image/"):
        raise ImageOptimizationError("Data URL debe inicio con 'data:image/'")
    
    try:
        header, data = data_url.split(",", 1)
        mime_type = header.split(":")[1].split(";")[0]  # "image/png"
        image_data = base64.b64decode(data)
        return mime_type, image_data
    except (ValueError, IndexError) as e:
        raise ImageOptimizationError(f"Data URL inválida: {e}")


def fix_image_orientation(image: Image.Image) -> Image.Image:
    """Corrige la orientación de la imagen basada en EXIF."""
    try:
        from PIL import Image  
        exif = image.getexif()
        if exif is None:
            return image
            
        orientation = exif.get(0x0112)  # Orientation tag
        if orientation == 3:
            image = image.rotate(180, expand=True)
        elif orientation == 6:
            image = image.rotate(270, expand=True)
        elif orientation == 8:
            image = image.rotate(90, expand=True)
    except Exception:
        pass  # Si falla EXIF, continuamos sin rotación
    return image


def optimize_image(
    data_url: str,
    image_type: str = "default",
    target_width: Optional[int] = None,
) -> str:
    """
    Optimiza una imagen desde data URL, comprimiendo a límite de peso.
    
    Args:
        data_url: Data URL de entrada
        image_type: Tipo de imagen (profile, document, gallery, default)
        target_width: Ancho máximo en píxeles (None = sin redimensionar)
        
    Returns:
        Data URL optimizada
        
    Raises:
        ImageOptimizationError: Si la optimización falla
    """
    try:
        mime_type, image_data = validate_data_url(data_url)
        
        # Abre imagen
        img = Image.open(io.BytesIO(image_data))
        
        # Fijar orientación
        img = fix_image_orientation(img)
        
        # Convertir a RGB si tiene trasparencia y es JPEG
        if img.mode in ("RGBA", "LA", "P") and "jpeg" in mime_type.lower():
            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = rgb_img
        
        # Redimensionar si necesario
        size_limit = IMAGE_LIMITS.get(image_type, IMAGE_LIMITS["default"])
        quality = COMPRESSION_QUALITY.get(image_type, COMPRESSION_QUALITY["default"])
        
        if target_width:
            ratio = target_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
        elif image_type == "profile" and img.width > 512:
            ratio = 512 / img.width
            new_height = int(img.height * ratio)
            img = img.resize((512, new_height), Image.Resampling.LANCZOS)
        
        # Determinar formato de salida
        if image_type in {"profile", "gallery"}:
            output_format = "WEBP"
        elif image_type == "document":
            output_format = "PNG" if "png" in mime_type.lower() else "JPEG"
        else:
            output_format = "PNG" if "png" in mime_type.lower() else "WEBP" if "webp" in mime_type.lower() else "JPEG"
        
        # Comprimir iterativamente hasta conseguir el tamaño deseado
        current_quality = quality
        while current_quality > 10:
            output = io.BytesIO()
            save_kwargs = {"format": output_format}
            if output_format == "JPEG":
                save_kwargs["quality"] = current_quality
                save_kwargs["optimize"] = True
            elif output_format == "WEBP":
                save_kwargs["quality"] = current_quality
                save_kwargs["method"] = 6
            elif output_format == "PNG":
                save_kwargs["optimize"] = True
            
            img.save(output, **save_kwargs)
            output_size = output.tell()
            
            if output_size <= size_limit or current_quality <= 20:
                break
            current_quality -= 5
        
        # Resultado final
        output.seek(0)
        optimized_data = base64.b64encode(output.read()).decode()
        output_mime = "image/jpeg" if output_format == "JPEG" else f"image/{output_format.lower()}"
        return f"data:{output_mime};base64,{optimized_data}"
        
    except ImageOptimizationError:
        raise
    except Exception as e:
        raise ImageOptimizationError(f"Error optimizando imagen: {e}")


def save_upload_file(
    data_url: str,
    filename: str,
    image_type: str = "default",
) -> str:
    """
    Guarda un archivo de imagen en el filesystem y retorna su ruta.
    
    Args:
        data_url: Data URL de entrada
        filename: Nombre del archivo (sin extension, será añadida)
        image_type: Tipo de imagen
        
    Returns:
        Ruta relativa del archivo guardado
    """
    try:
        mime_type, image_data = validate_data_url(data_url)
        
        # Crear directorio si no existe
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Optimizar primero
        optimized = optimize_image(data_url, image_type)
        _, optimized_data = optimized.split(",", 1)
        binary_data = base64.b64decode(optimized_data)
        
        # Guardar archivo
        ext = "png" if "png" in mime_type else "webp" if "webp" in mime_type else "jpg"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = STORAGE_DIR / f"{filename}_{timestamp}.{ext}"
        
        filepath.write_bytes(binary_data)
        
        # Retornar ruta relativa
        return f"/storage/uploads/{filepath.name}"
        
    except Exception as e:
        raise ImageOptimizationError(f"Error guardando imagen: {e}")


def build_data_url_from_base64(base64_str: str, mime_type: str = "image/jpeg") -> str:
    """Construye una data URL a partir de base64 puro."""
    return f"data:{mime_type};base64,{base64_str}"


def get_image_info(data_url: str) -> dict:
    """
    Extrae información de una imagen.
    
    Returns:
        Diccionario con tamaño, formato, dimensiones, etc.
    """
    try:
        mime_type, image_data = validate_data_url(data_url)
        img = Image.open(io.BytesIO(image_data))
        
        return {
            "mime_type": mime_type,
            "format": img.format,
            "width": img.width,
            "height": img.height,
            "size_bytes": len(image_data),
            "size_kb": round(len(image_data) / 1024, 2),
            "mode": img.mode,
        }
    except Exception as e:
        raise ImageOptimizationError(f"Error extrayendo info: {e}")


def batch_optimize_images(data_urls: list[str], image_type: str = "default") -> list[str]:
    """Optimiza múltiples imágenes en batch."""
    return [optimize_image(url, image_type) for url in data_urls]

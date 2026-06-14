"""Modelo de salida para `contiinia exportar`."""

from pydantic import BaseModel


class ExportarPeriodo(BaseModel):
    fecha_min: str | None
    fecha_max: str | None


class ExportarResult(BaseModel):
    archivo_generado: str
    hojas: list[str] = ["Resumen", "Detalle_CFDI", "Errores"]
    total_cfdi_exitosos: int
    total_cfdi_errores: int
    periodo: ExportarPeriodo

"""Modelos Pydantic para contiinia lote y contiinia duplicados — Hito 4.6."""

from typing import Any

from pydantic import BaseModel

from contiinia.models.cfdi import CfdiXml


class LoteErrorItem(BaseModel):
    error: str
    archivo: str | None = None
    detalle: str


class LoteResultado(BaseModel):
    archivo: str
    estado: str  # "ok" | "error"
    datos: CfdiXml | None = None
    error: LoteErrorItem | None = None


class LoteResult(BaseModel):
    directorio: str
    recursivo: bool
    total_archivos: int
    exitosos: int
    errores: int
    resultados: list[LoteResultado]


class DuplicadoAdvertencia(BaseModel):
    archivo: str
    motivo: str


class DuplicadoItem(BaseModel):
    uuid: str
    ocurrencias: int
    archivos: list[str]


class DuplicadosResult(BaseModel):
    directorio: str
    recursivo: bool
    total_archivos_procesados: int
    total_duplicados: int
    duplicados: list[DuplicadoItem]
    advertencias: list[DuplicadoAdvertencia]

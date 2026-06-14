"""Modelos Pydantic para `contiinia tabla` — CA-TAB-01..09."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_serializer


class TablaRow(BaseModel):
    """Una fila normalizada de la tabla de conceptos."""

    clave_prod_serv: str | None = None
    descripcion: str | None = None
    cantidad: Decimal | None = None
    valor_unitario: Decimal | None = None
    importe: Decimal | None = None
    impuesto: str | None = None
    tasa: str | None = None
    columnas_extra: dict[str, Any] = {}

    @field_serializer("cantidad", "valor_unitario", "importe")
    def serialize_decimal(self, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None


class TablaResult(BaseModel):
    """Resultado del parseo de una tabla de conceptos."""

    archivo: str
    total_registros: int
    columnas_detectadas: list[str]
    registros: list[TablaRow]

    model_config = {
        "json_schema_extra": {"description": "Resultado de parseo de tabla de conceptos"}
    }

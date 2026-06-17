"""Modelos Pydantic para `contiinia tabla` — CA-TAB-01..09."""

from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_serializer


class AdvertenciaImporteInconsistente(BaseModel):
    tipo: Literal["importe_inconsistente"] = "importe_inconsistente"
    fila: int
    importe_declarado: str
    importe_calculado: str
    diferencia: str


class AdvertenciaTasaNoNumerica(BaseModel):
    tipo: Literal["tasa_no_numerica"] = "tasa_no_numerica"
    fila: int
    valor_encontrado: str


AdvertenciaTabla = Annotated[
    AdvertenciaImporteInconsistente | AdvertenciaTasaNoNumerica | str,
    Field(union_mode="left_to_right"),
]


class TablaRow(BaseModel):
    """Una fila normalizada de la tabla de conceptos."""

    model_config = ConfigDict(populate_by_name=True)

    _tasa_col_presente: bool = PrivateAttr(default=False)

    fila: int
    clave_prod_serv: str | None = None
    descripcion: str | None = None
    cantidad: Decimal | None = None
    valor_unitario: Decimal | None = None
    importe: Decimal | None = None
    tasa: str | None = None
    iva_estimado: Decimal | None = None
    columnas_extra: dict[str, Any] = {}

    @field_serializer("cantidad", "valor_unitario", "importe")
    def serialize_decimal(self, v: Decimal | None) -> str | None:
        return str(v) if v is not None else None

    @field_serializer("iva_estimado")
    def serialize_iva(self, v: Decimal | None) -> str | None:
        return f"{v:.2f}" if v is not None else None


class TablaResult(BaseModel):
    """Resultado del parseo de una tabla de conceptos."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={"description": "Resultado de parseo de tabla de conceptos"},
    )

    archivo: str
    formato: str
    total_registros: int
    columnas_detectadas: list[str]
    registros: list[TablaRow]
    total_iva_estimado: Decimal | None = None
    advertencias: list[AdvertenciaTabla] = []

    @field_serializer("total_iva_estimado")
    def serialize_total_iva(self, v: Decimal | None) -> str | None:
        return f"{v:.2f}" if v is not None else None

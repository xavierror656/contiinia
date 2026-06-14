"""Modelos Pydantic para `contiinia resumen` — Hito 4.7."""

from decimal import Decimal

from pydantic import BaseModel, field_serializer


class IvaTrasladadoPorTasa(BaseModel):
    tasa: str  # "0.160000", "0.080000", "0.000000", o "Exento"
    base: Decimal
    importe: Decimal

    @field_serializer("base", "importe")
    def serialize_decimal(self, v: Decimal) -> str:
        return str(v)


class ResumenImpuestos(BaseModel):
    iva_trasladado_por_tasa: list[IvaTrasladadoPorTasa] = []
    total_iva_trasladado: Decimal
    total_iva_retenido: Decimal
    total_isr_retenido: Decimal

    @field_serializer("total_iva_trasladado", "total_iva_retenido", "total_isr_retenido")
    def serialize_decimal(self, v: Decimal) -> str:
        return str(v)


class ResumenConteo(BaseModel):
    total_archivos: int
    exitosos: int
    errores: int
    por_tipo: dict[str, int]


class ResumenTotales(BaseModel):
    subtotal_ingresos: Decimal
    subtotal_egresos: Decimal
    total_neto: Decimal

    @field_serializer("subtotal_ingresos", "subtotal_egresos", "total_neto")
    def serialize_decimal(self, v: Decimal) -> str:
        return str(v)


class ResumenPeriodo(BaseModel):
    fecha_min: str | None
    fecha_max: str | None


class PagoPpdSinComplemento(BaseModel):
    count: int
    uuids: list[str]


class ResumenNomina(BaseModel):
    count: int
    total_percepciones: Decimal
    advertencia: str

    @field_serializer("total_percepciones")
    def serialize_decimal(self, v: Decimal) -> str:
        return str(v)


class ResumenTraslados(BaseModel):
    count: int


class ErrorDetalle(BaseModel):
    archivo: str
    error: str
    detalle: str


class ResumenLote(BaseModel):
    """Resultado del comando `contiinia resumen`."""

    directorio: str
    recursivo: bool
    moneda_base: str
    periodo: ResumenPeriodo
    conteo: ResumenConteo
    totales: ResumenTotales
    impuestos: ResumenImpuestos
    pagos_ppd_sin_complemento: PagoPpdSinComplemento
    nomina: ResumenNomina
    traslados: ResumenTraslados
    errores_detalle: list[ErrorDetalle] = []
    advertencias: list[str] = []

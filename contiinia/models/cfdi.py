"""Modelos Pydantic para CFDI 4.0 — Hito 4.4."""

from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer


class Traslado(BaseModel):
    impuesto: str
    tipo_factor: str
    tasa_o_cuota: Decimal | None = None
    base: Decimal
    importe: Decimal | None = None

    @field_serializer("tasa_o_cuota", "base", "importe")
    def serialize_decimal(self, v: Decimal | None) -> str | None:  # noqa: D102
        return str(v) if v is not None else None


class Retencion(BaseModel):
    impuesto: str
    importe: Decimal

    @field_serializer("importe")
    def serialize_decimal(self, v: Decimal) -> str:  # noqa: D102
        return str(v)


class Concepto(BaseModel):
    clave_prod_serv: str
    no_identificacion: str | None = None
    cantidad: Decimal
    clave_unidad: str
    unidad: str | None = None
    descripcion: str
    valor_unitario: Decimal
    importe: Decimal
    descuento: Decimal | None = None
    objeto_imp: str | None = None
    traslados: list[Traslado] = []
    retenciones: list[Retencion] = []

    @field_serializer("cantidad", "valor_unitario", "importe", "descuento")
    def serialize_decimal(self, v: Decimal | None) -> str | None:  # noqa: D102
        return str(v) if v is not None else None


class Emisor(BaseModel):
    rfc: str
    nombre: str | None = None
    regimen_fiscal: str


class Receptor(BaseModel):
    rfc: str
    nombre: str | None = None
    domicilio_fiscal_receptor: str | None = None
    residencia_fiscal: str | None = None
    num_reg_id_trib: str | None = None
    regimen_fiscal_receptor: str | None = None
    uso_cfdi: str


class ComplementoTimbre(BaseModel):
    uuid: str
    fecha_timbrado: str
    rfc_prov_certif: str
    no_certificado_sat: str


class CfdiXml(BaseModel):
    model_config = {"populate_by_name": True, "serialize_by_alias": True}

    version: str
    serie: str | None = None
    folio: str | None = None
    fecha: str
    sello: str | None = None
    forma_pago: str | None = None
    no_certificado: str
    certificado: str | None = None
    subtotal: Decimal
    descuento: Decimal | None = None
    moneda: str
    tipo_cambio: Decimal | None = None
    total: Decimal
    tipo_de_comprobante: str = Field(alias="tipo_comprobante")
    exportacion: str | None = None
    metodo_pago: str | None = None
    lugar_expedicion: str
    emisor: Emisor
    receptor: Receptor
    conceptos: list[Concepto]
    total_impuestos_trasladados: Decimal | None = None
    total_impuestos_retenidos: Decimal | None = None
    traslados_globales: list[Traslado] = []
    retenciones_globales: list[Retencion] = []
    timbre: ComplementoTimbre | None = None

    @field_serializer(
        "subtotal",
        "descuento",
        "tipo_cambio",
        "total",
        "total_impuestos_trasladados",
        "total_impuestos_retenidos",
    )
    def serialize_decimal(self, v: Decimal | None) -> str | None:  # noqa: D102
        return str(v) if v is not None else None

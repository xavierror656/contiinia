"""Tipos y modelos base compartidos por todos los modelos del dominio."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

# DecimalStr: Decimal serializado como string en JSON (Principio 3 — sin float para importes).
DecimalStr = Annotated[Decimal, PlainSerializer(lambda v: str(v), return_type=str)]


class ErrorResponse(BaseModel):
    """Respuesta de error estructurada (Principio 2 — toda salida es JSON)."""

    model_config = ConfigDict(populate_by_name=True)

    error: str        # snake_case: "archivo_no_encontrado", "xml_malformado", etc.
    archivo: str | None  # ruta absoluta o null
    detalle: str      # mensaje legible; nunca traceback

"""Modelo RfcValidation — salida de `contiinia rfc`."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class RfcValidation(BaseModel):
    """Resultado de la validación de un RFC mexicano.

    El campo `valido` discrimina entre éxito y fallo:
    - valido=True: campos `tipo` y `longitud` están presentes.
    - valido=False: campo `motivo` indica la razón del rechazo.
    """

    model_config = ConfigDict(populate_by_name=True)

    rfc: str
    valido: bool

    # Presentes cuando valido=True:
    tipo: Literal["fisica", "moral", "generico_nacional", "generico_extranjero"] | None = None
    longitud: int | None = None

    # Presentes cuando valido=False:
    motivo: Literal[
        "longitud_incorrecta",
        "caracteres_invalidos",
        "fecha_invalida",
        "digito_verificador_incorrecto",
        "fecha_futura",
    ] | None = None

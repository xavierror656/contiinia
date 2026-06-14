"""Comando `contiinia rfc` — valida la estructura de un RFC mexicano."""

import json
import sys
from typing import Annotated

import typer

from contiinia.errors import ExitCode, emit_error
from contiinia.errors import SystemError as ContiiniaSystemError
from contiinia.models.rfc import RfcValidation
from contiinia.parsers.rfc import validar_rfc


def cmd_rfc(
    rfc_value: Annotated[str, typer.Argument(help="RFC a validar (12 o 13 caracteres)")],
    schema: Annotated[bool, typer.Option("--schema", help="Emitir JSON Schema del modelo")] = False,
) -> None:
    """Valida la estructura formal de un RFC mexicano (offline, sin consulta al SAT)."""
    if schema:
        print(json.dumps(RfcValidation.model_json_schema(), ensure_ascii=False, indent=2), flush=True)
        raise typer.Exit(0)

    try:
        resultado = validar_rfc(rfc_value)
        print(resultado.model_dump_json(exclude_none=True), flush=True)
    except Exception as exc:
        emit_error(ContiiniaSystemError(f"Error inesperado: {exc}", archivo=None))

    if not resultado.valido:
        sys.exit(ExitCode.BUSINESS)

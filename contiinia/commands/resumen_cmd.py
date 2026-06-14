"""Comando `contiinia resumen` — Hito 4.7."""

import json
import sys
from pathlib import Path
from typing import Annotated

import typer

from contiinia.errors import ContiiniaError, emit_error
from contiinia.errors import SystemError as ContiiniaSystemError
from contiinia.models.resumen import ResumenLote
from contiinia.parsers.resumen import calcular_resumen


def cmd_resumen(
    directorio: Annotated[Path, typer.Argument(help="Directorio con archivos XML CFDI")],
    recursivo: Annotated[
        bool,
        typer.Option("--recursivo", help="Recorre subdirectorios en profundidad"),
    ] = False,
    schema: Annotated[
        bool,
        typer.Option("--schema", help="Emite JSON Schema del modelo de salida"),
    ] = False,
) -> None:
    """Agrega totales fiscales de todos los CFDI 4.0 de un directorio."""
    if schema:
        print(json.dumps(ResumenLote.model_json_schema(), indent=2), flush=True)
        raise typer.Exit(0)

    try:
        result = calcular_resumen(directorio, recursivo=recursivo)
        print(result.model_dump_json(exclude_none=False), flush=True)
    except ContiiniaError as exc:
        emit_error(exc)
    except Exception as exc:
        emit_error(ContiiniaSystemError(f"Error inesperado: {exc}", archivo=str(directorio)))

"""Comandos `contiinia lote` y `contiinia duplicados` — Hito 4.6."""

import json
import sys
from pathlib import Path
from typing import Annotated

import typer

from contiinia.errors import (
    ContiiniaError,
    DirectorioNoEncontradoError,
    emit_error,
)
from contiinia.models.lote import DuplicadosResult, LoteResult
from contiinia.parsers.lote import detectar_duplicados, parsear_lote


def cmd_lote(
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
    """Parsea todos los XML en un directorio y emite JSON con resultados por archivo."""
    if schema:
        print(json.dumps(LoteResult.model_json_schema(), indent=2), flush=True)
        raise typer.Exit(0)

    try:
        result = parsear_lote(directorio, recursivo=recursivo)
        print(result.model_dump_json(exclude_none=True), flush=True)
    except ContiiniaError as exc:
        emit_error(exc)
    except Exception as exc:
        from contiinia.errors import SystemError as CSysError
        emit_error(CSysError(f"Error inesperado: {exc}", archivo=str(directorio)))


def cmd_duplicados(
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
    """Detecta UUIDs duplicados entre todos los XML de un directorio."""
    if schema:
        print(json.dumps(DuplicadosResult.model_json_schema(), indent=2), flush=True)
        raise typer.Exit(0)

    try:
        result = detectar_duplicados(directorio, recursivo=recursivo)
        print(result.model_dump_json(exclude_none=True), flush=True)
    except ContiiniaError as exc:
        emit_error(exc)
    except Exception as exc:
        from contiinia.errors import SystemError as CSysError
        emit_error(CSysError(f"Error inesperado: {exc}", archivo=str(directorio)))

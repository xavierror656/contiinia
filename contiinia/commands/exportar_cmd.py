"""Comando `contiinia exportar`."""

import json
from pathlib import Path
from typing import Annotated

import typer

from contiinia.errors import (
    BusinessError,
    ContiiniaError,
    UnsupportedVersionError,
    emit_error,
)
from contiinia.errors import SystemError as ContiiniaSystemError
from contiinia.models.exportar import ExportarResult
from contiinia.parsers.exportar import generar_exportar


def cmd_exportar(
    directorio: Annotated[Path, typer.Argument(help="Directorio con archivos CFDI XML")],
    salida: Annotated[Path, typer.Argument(help="Archivo Excel de salida (.xlsx)")],
    recursivo: Annotated[
        bool,
        typer.Option("--recursivo", help="Incluir subdirectorios"),
    ] = False,
    schema: Annotated[
        bool,
        typer.Option("--schema", help="Emitir JSON Schema del modelo"),
    ] = False,
) -> None:
    """Genera reporte Excel de CFDI desde un directorio."""
    if schema:
        print(json.dumps(ExportarResult.model_json_schema(), indent=2), flush=True)
        raise typer.Exit(0)

    try:
        result = generar_exportar(directorio, salida, recursivo=recursivo)
        print(result.model_dump_json(), flush=True)
    except UnsupportedVersionError as exc:
        emit_error(exc)
    except BusinessError as exc:
        emit_error(exc)
    except ContiiniaSystemError as exc:
        emit_error(exc)
    except ContiiniaError as exc:
        emit_error(exc)
    except Exception as exc:
        emit_error(ContiiniaSystemError(f"Error inesperado: {exc}", archivo=str(salida)))

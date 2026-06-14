"""Comando `contiinia xml` — parsea un CFDI 4.0 XML y emite JSON."""

import json
import sys
from pathlib import Path
from typing import Annotated

import typer

from contiinia.errors import (
    ArchivoNoEncontradoError,
    BusinessError,
    ContiiniaError,
    ExitCode,
    SystemError as ContiiniaSystemError,
    UnsupportedVersionError,
    emit_error,
)
from contiinia.models.cfdi import CfdiXml
from contiinia.parsers.xml import parsear_xml


def cmd_xml(
    archivo: Annotated[Path | None, typer.Argument(help="Ruta al archivo CFDI XML")] = None,
    schema: Annotated[bool, typer.Option("--schema", help="Emite JSON Schema del modelo")] = False,
) -> None:
    """Parsea un CFDI 4.0 XML y emite un objeto JSON con los campos fiscales."""
    if schema:
        print(json.dumps(CfdiXml.model_json_schema(), indent=2), flush=True)
        raise typer.Exit(0)
    if archivo is None:
        typer.echo("Error: Falta el argumento 'ARCHIVO'.", err=True)
        raise typer.Exit(1)

    # Verificar existencia del archivo antes de parsear
    if not archivo.exists():
        emit_error(ArchivoNoEncontradoError(
            f"Archivo no encontrado: {archivo}",
            archivo=str(archivo),
        ))

    try:
        result = parsear_xml(archivo)
        print(result.model_dump_json(exclude_none=True), flush=True)
    except UnsupportedVersionError as exc:
        emit_error(exc)
    except BusinessError as exc:
        emit_error(exc)
    except ContiiniaSystemError as exc:
        emit_error(exc)
    except ContiiniaError as exc:
        emit_error(exc)
    except Exception as exc:
        from contiinia.errors import SystemError as CSysError
        emit_error(CSysError(f"Error inesperado: {exc}", archivo=str(archivo)))

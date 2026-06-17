"""Comando `contiinia tabla` — parsea CSV/XLSX de conceptos y emite JSON."""

import json
from pathlib import Path
from typing import Annotated

import typer

from contiinia.errors import (
    BusinessError,
    ContiiniaError,
    emit_error,
)
from contiinia.errors import (
    SystemError as ContiiniaSystemError,
)
from contiinia.models.tabla import TablaResult
from contiinia.parsers.tabla import parsear_tabla


def cmd_tabla(
    archivo: Annotated[Path, typer.Argument(help="Archivo CSV o XLSX con tabla de conceptos")],
    schema: Annotated[
        bool, typer.Option("--schema", help="Emite JSON Schema del modelo de salida")
    ] = False,
) -> None:
    """Parsea una tabla de conceptos CSV o XLSX y emite JSON normalizado."""
    if schema:
        print(json.dumps(TablaResult.model_json_schema(), indent=2), flush=True)
        raise typer.Exit(0)

    try:
        result = parsear_tabla(archivo)
        _data = json.loads(result.model_dump_json(exclude_none=True))
        for _i, _row in enumerate(result.registros):
            if _row._tasa_col_presente and "iva_estimado" not in _data["registros"][_i]:
                _data["registros"][_i]["iva_estimado"] = None
        print(json.dumps(_data), flush=True)
    except BusinessError as exc:
        emit_error(exc)
    except ContiiniaSystemError as exc:
        emit_error(exc)
    except ContiiniaError as exc:
        emit_error(exc)
    except Exception as exc:
        emit_error(ContiiniaSystemError(f"Error inesperado: {exc}", archivo=str(archivo)))

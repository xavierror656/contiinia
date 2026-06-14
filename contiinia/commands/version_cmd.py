"""Comando `contiinia version` — emite VersionInfo como JSON a stdout."""

import json
from typing import Annotated

import typer

from contiinia.models.version import VersionInfo


def cmd_version(
    schema: Annotated[bool, typer.Option("--schema", help="Emitir JSON Schema del modelo")] = False,
) -> None:
    """Emite la versión del CLI y el entorno de ejecución."""
    if schema:
        print(json.dumps(VersionInfo.model_json_schema(), ensure_ascii=False, indent=2), flush=True)
        raise typer.Exit(0)

    print(VersionInfo().model_dump_json(), flush=True)
    raise typer.Exit(0)

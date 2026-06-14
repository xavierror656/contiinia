"""Comando `contiinia version` — emite VersionInfo como JSON a stdout."""

import json
import platform
import sys
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

    info = {
        "version": VersionInfo().version,
        "python": sys.version.split()[0],
        "platform": platform.system().lower(),
    }
    print(json.dumps(info, ensure_ascii=False), flush=True)
    raise typer.Exit(0)

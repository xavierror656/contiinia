"""CLI principal de contiinia — registra subcomandos; sin lógica de negocio."""

import atexit
import json
import sys

import typer

# PyInstaller frozen binaries: force line-buffered stdout so output flushes
# before the process exits even without a TTY (e.g. inside Docker pipes).
if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)
def _safe_flush(stream: object) -> None:
    try:
        if stream is not None:
            stream.flush()  # type: ignore[union-attr]
    except Exception:
        pass

atexit.register(_safe_flush, sys.stdout)
atexit.register(_safe_flush, sys.stderr)

from contiinia.commands.exportar_cmd import cmd_exportar
from contiinia.commands.lote_cmd import cmd_duplicados, cmd_lote
from contiinia.commands.resumen_cmd import cmd_resumen
from contiinia.commands.rfc_cmd import cmd_rfc
from contiinia.commands.tabla_cmd import cmd_tabla
from contiinia.commands.version_cmd import cmd_version
from contiinia.commands.xml_cmd import cmd_xml

app = typer.Typer(
    name="contiinia",
    help="CLI para procesamiento de CFDI 4.0.",
    pretty_exceptions_show_locals=False,  # Principio 6: nunca tracebacks al usuario
    pretty_exceptions_enable=False,
    no_args_is_help=False,
    invoke_without_command=True,
)


@app.callback()
def _callback(ctx: typer.Context) -> None:
    """contiinia — procesamiento de CFDI 4.0."""
    if ctx.invoked_subcommand is None:
        # Constitución Principio 2: toda salida es JSON; nunca texto libre a stdout.
        payload = {
            "error": "subcomando_requerido",
            "archivo": None,
            "detalle": "Se requiere un subcomando. Comandos disponibles: version, rfc, xml, tabla, lote, duplicados, resumen, exportar",
        }
        print(json.dumps(payload, ensure_ascii=False), file=sys.stderr, flush=True)
        raise typer.Exit(1)


app.command("version", help="Emite la versión del CLI y el entorno.")(cmd_version)
app.command("rfc", help="Valida la estructura formal de un RFC mexicano.")(cmd_rfc)
app.command("xml", help="Parsea un CFDI 4.0 XML y emite JSON fiscal.")(cmd_xml)
app.command("tabla", help="Parsea una tabla de conceptos CSV o XLSX y emite JSON.")(cmd_tabla)
app.command("lote", help="Parsea todos los XML de un directorio y emite JSON.")(cmd_lote)
app.command("duplicados", help="Detecta UUIDs duplicados en un directorio de CFDIs.")(cmd_duplicados)
app.command("resumen", help="Agrega totales fiscales de todos los CFDI 4.0 de un directorio.")(cmd_resumen)
app.command("exportar", help="Genera reporte Excel de CFDI desde un directorio.")(cmd_exportar)

if __name__ == "__main__":
    app()

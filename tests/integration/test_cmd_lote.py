"""Pruebas de integración para `contiinia lote` y `contiinia duplicados` — Hito 4.6."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from contiinia.cli import app

runner = CliRunner()

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# contiinia lote
# ---------------------------------------------------------------------------


def test_cmd_lote_exit_0() -> None:
    """contiinia lote <fixtures/> → exit 0."""
    result = runner.invoke(app, ["lote", str(FIXTURES)])
    assert result.exit_code == 0, f"output: {result.output}"


def test_cmd_lote_json_valido() -> None:
    """contiinia lote emite JSON válido."""
    result = runner.invoke(app, ["lote", str(FIXTURES)])
    data = json.loads(result.output)
    assert isinstance(data, dict)


def test_cmd_lote_tiene_resultados() -> None:
    """JSON tiene campo 'resultados' con items."""
    result = runner.invoke(app, ["lote", str(FIXTURES)])
    data = json.loads(result.output)
    assert "resultados" in data
    assert isinstance(data["resultados"], list)
    assert len(data["resultados"]) >= 5


def test_cmd_lote_campos_requeridos() -> None:
    """Campos directorio, total_archivos, exitosos, errores, resultados presentes."""
    result = runner.invoke(app, ["lote", str(FIXTURES)])
    data = json.loads(result.output)
    for campo in ("directorio", "total_archivos", "exitosos", "errores", "resultados"):
        assert campo in data, f"Falta campo: {campo}"


def test_cmd_lote_exitosos_mayor_igual_tres() -> None:
    """Al menos 3 archivos exitosos en fixtures."""
    result = runner.invoke(app, ["lote", str(FIXTURES)])
    data = json.loads(result.output)
    assert data["exitosos"] >= 3


def test_cmd_lote_items_con_error_tienen_error_obj() -> None:
    """Items con estado='error' tienen objeto 'error' no nulo."""
    result = runner.invoke(app, ["lote", str(FIXTURES)])
    data = json.loads(result.output)
    for item in data["resultados"]:
        if item["estado"] == "error":
            assert "error" in item
            assert item["error"] is not None


def test_cmd_lote_directorio_no_existe_exit_3() -> None:
    """Directorio no existente → exit 3 (CA-LOT-03)."""
    result = runner.invoke(app, ["lote", "/tmp/no_existe_xyzcontiinia"])
    assert result.exit_code == 3


def test_cmd_lote_directorio_no_existe_stderr_json() -> None:
    """Directorio no existente → stderr/output contiene JSON de error."""
    result = runner.invoke(app, ["lote", "/tmp/no_existe_xyzcontiinia"])
    output = result.output
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("{"):
            data = json.loads(line)
            assert "error" in data
            break


def test_cmd_lote_schema_exit_0() -> None:
    """contiinia lote --schema → JSON Schema, exit 0 (CA-LOT-08)."""
    result = runner.invoke(app, ["lote", "--schema", str(FIXTURES)])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    assert isinstance(schema, dict)
    assert "properties" in schema or "title" in schema


def test_cmd_lote_schema_no_necesita_directorio_valido() -> None:
    """--schema funciona con cualquier argumento de directorio."""
    result = runner.invoke(app, ["lote", "--schema", "/tmp"])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    assert isinstance(schema, dict)


# ---------------------------------------------------------------------------
# contiinia duplicados
# ---------------------------------------------------------------------------


def test_cmd_duplicados_exit_0() -> None:
    """contiinia duplicados <fixtures/> → exit 0."""
    result = runner.invoke(app, ["duplicados", str(FIXTURES)])
    assert result.exit_code == 0, f"output: {result.output}"


def test_cmd_duplicados_json_valido() -> None:
    """contiinia duplicados emite JSON válido."""
    result = runner.invoke(app, ["duplicados", str(FIXTURES)])
    data = json.loads(result.output)
    assert isinstance(data, dict)


def test_cmd_duplicados_campos_requeridos() -> None:
    """Campos requeridos presentes en salida."""
    result = runner.invoke(app, ["duplicados", str(FIXTURES)])
    data = json.loads(result.output)
    for campo in ("directorio", "total_archivos_procesados", "total_duplicados", "duplicados"):
        assert campo in data, f"Falta campo: {campo}"


def test_cmd_duplicados_encuentra_duplicado() -> None:
    """cfdi_duplicado.xml y cfdi_ingreso.xml → duplicado detectado (CA-DUP-02)."""
    result = runner.invoke(app, ["duplicados", str(FIXTURES)])
    data = json.loads(result.output)
    assert data["total_duplicados"] >= 1
    assert len(data["duplicados"]) >= 1


def test_cmd_duplicados_ocurrencias_2() -> None:
    """El duplicado tiene ocurrencias >= 2."""
    result = runner.invoke(app, ["duplicados", str(FIXTURES)])
    data = json.loads(result.output)
    for dup in data["duplicados"]:
        assert dup["ocurrencias"] >= 2
        assert len(dup["archivos"]) >= 2


def test_cmd_duplicados_directorio_no_existe_exit_3() -> None:
    """Directorio no existente → exit 3 (CA-DUP-06)."""
    result = runner.invoke(app, ["duplicados", "/tmp/no_existe_xyzcontiinia"])
    assert result.exit_code == 3


def test_cmd_duplicados_schema_exit_0() -> None:
    """contiinia duplicados --schema → JSON Schema, exit 0 (CA-DUP-07)."""
    result = runner.invoke(app, ["duplicados", "--schema", str(FIXTURES)])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    assert isinstance(schema, dict)
    assert "properties" in schema or "title" in schema


def test_cmd_duplicados_schema_no_necesita_directorio_valido() -> None:
    """--schema funciona con cualquier argumento."""
    result = runner.invoke(app, ["duplicados", "--schema", "/tmp"])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    assert isinstance(schema, dict)

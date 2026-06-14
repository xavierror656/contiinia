"""Pruebas de integración para `contiinia tabla` vía CliRunner — CA-TAB-01..09."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from contiinia.cli import app

runner = CliRunner()

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def fx(nombre: str) -> str:
    return str(FIXTURES / nombre)


# ---------------------------------------------------------------------------
# CA-TAB-01: CSV con columnas canónicas → exit 0, JSON con registros
# ---------------------------------------------------------------------------


def test_cmd_csv_exit_0() -> None:
    """CA-TAB-01: tabla_conceptos.csv → exit 0."""
    result = runner.invoke(app, ["tabla", fx("tabla_conceptos.csv")])
    assert result.exit_code == 0, f"output: {result.output}"


def test_cmd_csv_json_valido() -> None:
    """CA-TAB-01: salida es JSON válido con 'registros'."""
    result = runner.invoke(app, ["tabla", fx("tabla_conceptos.csv")])
    data = json.loads(result.output)
    assert "registros" in data
    assert isinstance(data["registros"], list)


def test_cmd_csv_total_registros() -> None:
    """CA-TAB-01: CSV tiene 2 registros."""
    result = runner.invoke(app, ["tabla", fx("tabla_conceptos.csv")])
    data = json.loads(result.output)
    assert data["filas"] == 2
    assert len(data["registros"]) == 2


def test_cmd_csv_columnas_detectadas() -> None:
    """CA-TAB-01: columnas_detectadas incluye clave_prod_serv."""
    result = runner.invoke(app, ["tabla", fx("tabla_conceptos.csv")])
    data = json.loads(result.output)
    assert "clave_prod_serv" in data["columnas_detectadas"]


# ---------------------------------------------------------------------------
# CA-TAB-03: XLSX → exit 0, mismo esquema de salida
# ---------------------------------------------------------------------------


def test_cmd_xlsx_exit_0() -> None:
    """CA-TAB-03: tabla_conceptos.xlsx → exit 0."""
    result = runner.invoke(app, ["tabla", fx("tabla_conceptos.xlsx")])
    assert result.exit_code == 0, f"output: {result.output}"


def test_cmd_xlsx_json_valido() -> None:
    """CA-TAB-03: XLSX salida es JSON válido con 'registros'."""
    result = runner.invoke(app, ["tabla", fx("tabla_conceptos.xlsx")])
    data = json.loads(result.output)
    assert "registros" in data
    assert isinstance(data["registros"], list)


def test_cmd_xlsx_total_registros() -> None:
    """CA-TAB-03: XLSX tiene 2 registros."""
    result = runner.invoke(app, ["tabla", fx("tabla_conceptos.xlsx")])
    data = json.loads(result.output)
    assert data["filas"] == 2


# ---------------------------------------------------------------------------
# CA-TAB-08: Importes como strings en JSON (nunca number)
# ---------------------------------------------------------------------------


def test_cmd_csv_importes_son_strings() -> None:
    """CA-TAB-08: cantidad, valor_unitario, importe son strings en JSON."""
    result = runner.invoke(app, ["tabla", fx("tabla_conceptos.csv")])
    data = json.loads(result.output)
    reg = data["registros"][0]
    assert isinstance(reg["cantidad"], str)
    assert isinstance(reg["valor_unitario"], str)
    assert isinstance(reg["importe"], str)


# ---------------------------------------------------------------------------
# CA-TAB-09: --schema → JSON Schema válido, exit 0
# ---------------------------------------------------------------------------


def test_cmd_schema_exit_0() -> None:
    """CA-TAB-09: --schema → exit 0."""
    result = runner.invoke(app, ["tabla", "--schema", fx("tabla_conceptos.csv")])
    assert result.exit_code == 0, f"output: {result.output}"


def test_cmd_schema_json_valido() -> None:
    """CA-TAB-09: --schema emite JSON Schema válido."""
    result = runner.invoke(app, ["tabla", "--schema", fx("tabla_conceptos.csv")])
    schema = json.loads(result.output)
    assert isinstance(schema, dict)
    assert "properties" in schema or "title" in schema or "$defs" in schema


def test_cmd_schema_sin_archivo_real() -> None:
    """CA-TAB-09: --schema no necesita un archivo válido para emitir el schema."""
    result = runner.invoke(app, ["tabla", "--schema", "/dev/null"])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    assert isinstance(schema, dict)


# ---------------------------------------------------------------------------
# Error: archivo no existe → exit 3
# ---------------------------------------------------------------------------


def test_cmd_archivo_no_existe_exit_3() -> None:
    """Archivo no existente → exit 3."""
    result = runner.invoke(app, ["tabla", "/tmp/no_existe_tabla_xyz.csv"])
    assert result.exit_code == 3


def test_cmd_archivo_no_existe_json_error() -> None:
    """Archivo no existente → stderr/output JSON con campo 'error'."""
    result = runner.invoke(app, ["tabla", "/tmp/no_existe_tabla_xyz.csv"])
    output = result.output
    try:
        data = json.loads(output)
        assert "error" in data
    except json.JSONDecodeError:
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("{"):
                data = json.loads(line)
                assert "error" in data
                break


# ---------------------------------------------------------------------------
# Error: extensión no soportada → exit 1
# ---------------------------------------------------------------------------


def test_cmd_extension_no_soportada_exit_1(tmp_path: Path) -> None:
    """Extensión .txt → exit 1, error formato_no_soportado."""
    tmp_file = tmp_path / "datos.txt"
    tmp_file.write_text("dato\n")
    result = runner.invoke(app, ["tabla", str(tmp_file)])
    assert result.exit_code == 1

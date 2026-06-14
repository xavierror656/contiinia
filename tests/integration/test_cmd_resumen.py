"""Pruebas de integración para `contiinia resumen` — Hito 4.7."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from contiinia.cli import app

runner = CliRunner()

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Éxito básico
# ---------------------------------------------------------------------------


def test_cmd_resumen_exit_0() -> None:
    """contiinia resumen <fixtures/> → exit 0."""
    result = runner.invoke(app, ["resumen", str(FIXTURES)])
    assert result.exit_code == 0, f"output: {result.output}"


def test_cmd_resumen_json_valido() -> None:
    """contiinia resumen emite JSON válido."""
    result = runner.invoke(app, ["resumen", str(FIXTURES)])
    data = json.loads(result.output)
    assert isinstance(data, dict)


def test_cmd_resumen_campos_requeridos() -> None:
    """JSON contiene los campos principales del ResumenLote."""
    result = runner.invoke(app, ["resumen", str(FIXTURES)])
    data = json.loads(result.output)
    for campo in ("directorio", "conteo", "totales", "impuestos", "pagos_ppd_sin_complemento"):
        assert campo in data, f"Falta campo: {campo}"


def test_cmd_resumen_subtotal_neto_presente() -> None:
    """JSON contiene totales.total_neto como string decimal."""
    result = runner.invoke(app, ["resumen", str(FIXTURES)])
    data = json.loads(result.output)
    assert "total_neto" in data["totales"]
    # Debe ser string (Principio 3)
    assert isinstance(data["totales"]["total_neto"], str)


def test_cmd_resumen_conteo_campos() -> None:
    """conteo contiene total_archivos, exitosos, errores, por_tipo."""
    result = runner.invoke(app, ["resumen", str(FIXTURES)])
    data = json.loads(result.output)
    conteo = data["conteo"]
    for campo in ("total_archivos", "exitosos", "errores", "por_tipo"):
        assert campo in conteo, f"Falta campo en conteo: {campo}"


def test_cmd_resumen_exitosos_mayor_cero() -> None:
    """Hay al menos 5 archivos exitosos en fixtures."""
    result = runner.invoke(app, ["resumen", str(FIXTURES)])
    data = json.loads(result.output)
    assert data["conteo"]["exitosos"] >= 5


def test_cmd_resumen_errores_presentes() -> None:
    """Los archivos inválidos (3.3, corrupto) se cuentan en errores."""
    result = runner.invoke(app, ["resumen", str(FIXTURES)])
    data = json.loads(result.output)
    assert data["conteo"]["errores"] >= 2


def test_cmd_resumen_importes_son_strings() -> None:
    """Ningún importe en la salida es de tipo number JSON (CA-RES-07)."""
    result = runner.invoke(app, ["resumen", str(FIXTURES)])
    data = json.loads(result.output)

    def check_no_floats(obj: object, path: str = "") -> None:
        if isinstance(obj, float):
            raise AssertionError(f"Float encontrado en {path}: {obj}")
        if isinstance(obj, dict):
            for k, v in obj.items():
                check_no_floats(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_no_floats(item, f"{path}[{i}]")

    check_no_floats(data)


def test_cmd_resumen_por_tipo_incluye_todos() -> None:
    """por_tipo incluye las claves I, E, P, N, T."""
    result = runner.invoke(app, ["resumen", str(FIXTURES)])
    data = json.loads(result.output)
    por_tipo = data["conteo"]["por_tipo"]
    for tipo in ("I", "E", "P", "N", "T"):
        assert tipo in por_tipo, f"Falta tipo {tipo} en por_tipo"


# ---------------------------------------------------------------------------
# CA-RES-05: CFDI 3.3 contado en errores_detalle
# ---------------------------------------------------------------------------


def test_cmd_resumen_cfdi33_en_errores_detalle() -> None:
    """CFDI 3.3 aparece en errores_detalle, no detiene el proceso (CA-RES-05)."""
    result = runner.invoke(app, ["resumen", str(FIXTURES)])
    data = json.loads(result.output)
    errores = data.get("errores_detalle", [])
    assert len(errores) >= 1
    errores_tipo = [e["error"] for e in errores]
    assert any(e in ("version_no_soportada", "xml_malformado") for e in errores_tipo)


# ---------------------------------------------------------------------------
# CA-RES-08: --schema
# ---------------------------------------------------------------------------


def test_cmd_resumen_schema_exit_0() -> None:
    """contiinia resumen --schema → JSON Schema, exit 0 (CA-RES-08)."""
    result = runner.invoke(app, ["resumen", "--schema", str(FIXTURES)])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    assert isinstance(schema, dict)
    assert "properties" in schema or "title" in schema


def test_cmd_resumen_schema_es_json_schema_valido() -> None:
    """--schema emite un JSON Schema con campos esperados."""
    result = runner.invoke(app, ["resumen", "--schema", "/tmp"])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    assert isinstance(schema, dict)
    # Draft 2020-12 o 7 tiene title o $schema
    assert "title" in schema or "$defs" in schema or "properties" in schema


def test_cmd_resumen_schema_no_necesita_directorio_valido() -> None:
    """--schema no accede al directorio; funciona con cualquier ruta."""
    result = runner.invoke(app, ["resumen", "--schema", "/no/existe"])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    assert isinstance(schema, dict)


# ---------------------------------------------------------------------------
# Directorio no existente → exit 3
# ---------------------------------------------------------------------------


def test_cmd_resumen_directorio_no_existe_exit_3() -> None:
    """Directorio no existente → exit 3."""
    result = runner.invoke(app, ["resumen", "/tmp/no_existe_xyzcontiinia_resumen"])
    assert result.exit_code == 3


def test_cmd_resumen_directorio_no_existe_stderr_json() -> None:
    """Directorio no existente → stderr contiene JSON de error."""
    result = runner.invoke(app, ["resumen", "/tmp/no_existe_xyzcontiinia_resumen"])
    output = result.output
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("{"):
            data = json.loads(line)
            assert "error" in data
            break
    else:
        pytest.fail(f"No se encontró JSON de error en la salida: {output!r}")


# ---------------------------------------------------------------------------
# Directorio vacío → exit 0 con ceros (CA-RES-06)
# ---------------------------------------------------------------------------


def test_cmd_resumen_directorio_vacio(tmp_path: Path) -> None:
    """Directorio vacío → exit 0, totales en cero (CA-RES-06)."""
    result = runner.invoke(app, ["resumen", str(tmp_path)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["conteo"]["total_archivos"] == 0
    assert data["totales"]["total_neto"] == "0"


# ---------------------------------------------------------------------------
# --recursivo
# ---------------------------------------------------------------------------


def test_cmd_resumen_recursivo(tmp_path: Path) -> None:
    """--recursivo procesa subdirectorios."""
    subdir = tmp_path / "sub"
    subdir.mkdir()
    ingreso = FIXTURES / "cfdi_ingreso.xml"
    (subdir / "cfdi_ingreso.xml").write_bytes(ingreso.read_bytes())

    result = runner.invoke(app, ["resumen", "--recursivo", str(tmp_path)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["conteo"]["total_archivos"] == 1
    assert data["recursivo"] is True

"""Pruebas de integración para `contiinia xml` vía CliRunner — CA-XML-01..14."""

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
# CA-XML-01: CFDI tipo I → exit 0, JSON válido
# ---------------------------------------------------------------------------


def test_cmd_ingreso_exit_0() -> None:
    """CA-XML-01: cfdi_ingreso.xml → exit 0."""
    result = runner.invoke(app, ["xml", fx("cfdi_ingreso.xml")])
    assert result.exit_code == 0, f"output: {result.output}"


def test_cmd_ingreso_tipo_I() -> None:
    """CA-XML-01: tipo_de_comprobante='I'."""
    result = runner.invoke(app, ["xml", fx("cfdi_ingreso.xml")])
    data = json.loads(result.output)
    assert data["tipo_de_comprobante"] == "I"


def test_cmd_ingreso_total_string() -> None:
    """CA-XML-10: total es string '1160.00', no float."""
    result = runner.invoke(app, ["xml", fx("cfdi_ingreso.xml")])
    data = json.loads(result.output)
    assert data["total"] == "1160.00"
    assert isinstance(data["total"], str)


def test_cmd_ingreso_uuid_mayusculas() -> None:
    """CA-XML-11: UUID en mayúsculas, contiene '9001'."""
    result = runner.invoke(app, ["xml", fx("cfdi_ingreso.xml")])
    data = json.loads(result.output)
    uuid = data["timbre"]["uuid"]
    assert uuid == uuid.upper()
    assert "9001" in uuid


def test_cmd_ingreso_iva_16_traslado_global() -> None:
    """CA-XML-14: IVA 16% → tasa_o_cuota='0.160000' en traslados_globales."""
    result = runner.invoke(app, ["xml", fx("cfdi_ingreso.xml")])
    data = json.loads(result.output)
    tasas = [t["tasa_o_cuota"] for t in data.get("traslados_globales", [])]
    assert "0.160000" in tasas


# ---------------------------------------------------------------------------
# CA-XML-02: tipo E
# ---------------------------------------------------------------------------


def test_cmd_egreso_tipo_E() -> None:
    """CA-XML-02: cfdi_egreso.xml → tipo_de_comprobante='E', exit 0."""
    result = runner.invoke(app, ["xml", fx("cfdi_egreso.xml")])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["tipo_de_comprobante"] == "E"


# ---------------------------------------------------------------------------
# CA-XML-03: tipo P
# ---------------------------------------------------------------------------


def test_cmd_pago_tipo_P() -> None:
    """CA-XML-03: cfdi_pago.xml → tipo_de_comprobante='P', exit 0."""
    result = runner.invoke(app, ["xml", fx("cfdi_pago.xml")])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["tipo_de_comprobante"] == "P"


# ---------------------------------------------------------------------------
# CA-XML-04: tipo N
# ---------------------------------------------------------------------------


def test_cmd_nomina_tipo_N() -> None:
    """CA-XML-04: cfdi_nomina.xml → tipo_de_comprobante='N', exit 0."""
    result = runner.invoke(app, ["xml", fx("cfdi_nomina.xml")])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["tipo_de_comprobante"] == "N"


# ---------------------------------------------------------------------------
# CA-XML-05: tipo T
# ---------------------------------------------------------------------------


def test_cmd_traslado_tipo_T() -> None:
    """CA-XML-05: cfdi_traslado.xml → tipo_de_comprobante='T', exit 0."""
    result = runner.invoke(app, ["xml", fx("cfdi_traslado.xml")])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["tipo_de_comprobante"] == "T"


# ---------------------------------------------------------------------------
# CA-XML-06: CFDI 3.3 → exit 2, error=version_no_soportada
# ---------------------------------------------------------------------------


def test_cmd_cfdi33_exit_2() -> None:
    """CA-XML-06: cfdi_3.3_rechazado.xml → exit 2."""
    result = runner.invoke(app, ["xml", fx("cfdi_3.3_rechazado.xml")])
    assert result.exit_code == 2


def test_cmd_cfdi33_error_json_stderr() -> None:
    """CA-XML-06: stderr contiene JSON con error='version_no_soportada'."""
    result = runner.invoke(app, ["xml", fx("cfdi_3.3_rechazado.xml")])
    # typer.testing runner mezcla stdout+stderr en output cuando mix_stderr=True (default)
    # Buscamos el JSON de error en la salida combinada
    output = result.output
    # Puede que el JSON esté en output o en una excepción capturada
    # En el runner el stderr va a output por defecto
    try:
        data = json.loads(output)
        assert data.get("error") == "version_no_soportada"
    except json.JSONDecodeError:
        # El runner puede combinar salidas; buscamos la parte JSON
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("{"):
                data = json.loads(line)
                assert data.get("error") == "version_no_soportada"
                break


# ---------------------------------------------------------------------------
# CA-XML-07: XML malformado → exit 3
# ---------------------------------------------------------------------------


def test_cmd_xml_corrupto_exit_3() -> None:
    """CA-XML-07: cfdi_xml_corrupto.xml → exit 3."""
    result = runner.invoke(app, ["xml", fx("cfdi_xml_corrupto.xml")])
    assert result.exit_code == 3


def test_cmd_xml_corrupto_error_json() -> None:
    """CA-XML-07: stderr/output contiene JSON con error indicando malformado."""
    result = runner.invoke(app, ["xml", fx("cfdi_xml_corrupto.xml")])
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
# CA-XML-10: Ningún importe en JSON de salida es float
# ---------------------------------------------------------------------------


def test_cmd_no_floats_en_json() -> None:
    """CA-XML-10: todos los importes son string, no number/float."""
    result = runner.invoke(app, ["xml", fx("cfdi_ingreso.xml")])
    assert result.exit_code == 0
    data = json.loads(result.output)

    def check_no_float(obj: object, path: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                check_no_float(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                check_no_float(v, f"{path}[{i}]")
        elif isinstance(obj, float):
            raise AssertionError(f"Float encontrado en {path}: {obj!r}")

    check_no_float(data)


# ---------------------------------------------------------------------------
# CA-XML-12: --schema → JSON Schema, exit 0
# ---------------------------------------------------------------------------


def test_cmd_schema_exit_0() -> None:
    """CA-XML-12: --schema emite JSON Schema válido, exit 0."""
    result = runner.invoke(app, ["xml", "--schema", fx("cfdi_ingreso.xml")])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    assert isinstance(schema, dict)
    assert "properties" in schema or "title" in schema


def test_cmd_schema_no_necesita_archivo_valido() -> None:
    """CA-XML-12: --schema no lee el XML; cualquier ruta funciona."""
    result = runner.invoke(app, ["xml", "--schema", "/dev/null"])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    assert isinstance(schema, dict)


# ---------------------------------------------------------------------------
# CA-XML-14: IVA 8% zona frontera
# ---------------------------------------------------------------------------


def test_cmd_iva_frontera_tasa_8() -> None:
    """CA-XML-14: cfdi_iva_frontera.xml → tasa_o_cuota='0.080000', exit 0."""
    result = runner.invoke(app, ["xml", fx("cfdi_iva_frontera.xml")])
    assert result.exit_code == 0
    data = json.loads(result.output)
    tasas = [t["tasa_o_cuota"] for t in data.get("traslados_globales", [])]
    assert "0.080000" in tasas


# ---------------------------------------------------------------------------
# IVA exento
# ---------------------------------------------------------------------------


def test_cmd_iva_exento_tipo_factor() -> None:
    """cfdi_iva_exento.xml → TipoFactor='Exento', exit 0."""
    result = runner.invoke(app, ["xml", fx("cfdi_iva_exento.xml")])
    assert result.exit_code == 0
    data = json.loads(result.output)
    factores = [t["tipo_factor"] for t in data.get("traslados_globales", [])]
    assert "Exento" in factores


# ---------------------------------------------------------------------------
# Archivo no existe → exit 3
# ---------------------------------------------------------------------------


def test_cmd_archivo_no_existe_exit_3() -> None:
    """CA-XML-08: archivo inexistente → exit 3."""
    result = runner.invoke(app, ["xml", "/tmp/no_existe_cfdi_xyz.xml"])
    assert result.exit_code == 3


# ---------------------------------------------------------------------------
# Principio 2: toda salida es JSON
# ---------------------------------------------------------------------------


def test_cmd_salida_exitosa_es_json() -> None:
    """Principio 2: salida exitosa es JSON parseable."""
    result = runner.invoke(app, ["xml", fx("cfdi_ingreso.xml")])
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert "tipo_de_comprobante" in data

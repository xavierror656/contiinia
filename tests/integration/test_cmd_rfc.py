"""Pruebas de integración para `contiinia rfc` via CliRunner — CA-RFC-01..09."""

import json

from typer.testing import CliRunner

from contiinia.cli import app

runner = CliRunner()


def test_rfc_valido_exit_cero() -> None:
    """CA-RFC-04: RFC persona moral válido → exit 0, valido=true."""
    result = runner.invoke(app, ["rfc", "AAA010101AAA"])
    assert result.exit_code == 0, f"output: {result.output}"
    data = json.loads(result.output)
    assert data["valido"] is True
    assert data["tipo"] == "moral"


def test_rfc_generico_nacional_exit_cero() -> None:
    """CA-RFC-01: XAXX010101000 → exit 0, valido=true, tipo=generico_nacional."""
    result = runner.invoke(app, ["rfc", "XAXX010101000"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valido"] is True
    assert data["tipo"] == "generico_nacional"


def test_rfc_generico_extranjero_exit_cero() -> None:
    """CA-RFC-02: XEXX010101000 → exit 0, valido=true, tipo=generico_extranjero."""
    result = runner.invoke(app, ["rfc", "XEXX010101000"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valido"] is True
    assert data["tipo"] == "generico_extranjero"


def test_rfc_persona_fisica_exit_cero() -> None:
    """CA-RFC-03: RFC persona física válido → exit 0, tipo=fisica."""
    result = runner.invoke(app, ["rfc", "AAAA010101AAA"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valido"] is True
    assert data["tipo"] == "fisica"


def test_rfc_invalido_exit_uno() -> None:
    """CA-RFC-05: RFC inválido → exit 1, valido=false."""
    result = runner.invoke(app, ["rfc", "INVALIDO"])
    # El runner captura sys.exit; en typer.testing el exit_code refleja SystemExit
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valido"] is False


def test_rfc_longitud_invalida_exit_uno() -> None:
    """CA-RFC-05: RFC muy corto → exit 1, motivo=longitud_incorrecta."""
    result = runner.invoke(app, ["rfc", "AAA"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valido"] is False
    assert data["motivo"] == "longitud_incorrecta"


def test_rfc_con_guion_exit_uno() -> None:
    """CA-RFC-06: RFC con guión → exit 1, motivo=caracteres_invalidos."""
    result = runner.invoke(app, ["rfc", "AAA-010101-AAA"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valido"] is False
    assert data["motivo"] == "caracteres_invalidos"


def test_rfc_fecha_invalida_exit_uno() -> None:
    """CA-RFC-07: RFC con mes 13 → exit 1, motivo=fecha_invalida."""
    result = runner.invoke(app, ["rfc", "AAA991399AAA"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valido"] is False
    assert data["motivo"] == "fecha_invalida"


def test_rfc_schema_exit_cero() -> None:
    """CA-RFC-09: --schema emite JSON Schema válido, exit 0, sin validar RFC."""
    result = runner.invoke(app, ["rfc", "--schema", "AAA"])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    # El JSON Schema de pydantic v2 contiene 'properties' o 'title'
    assert "properties" in schema or "title" in schema


def test_rfc_schema_no_requiere_argumento() -> None:
    """CA-RFC-09: --schema puede invocarse sin RFC; no realiza validación de negocio."""
    # Cuando --schema está presente, el argumento rfc_value puede ser cualquier cosa
    result = runner.invoke(app, ["rfc", "CUALQUIER_COSA", "--schema"])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    assert isinstance(schema, dict)


def test_rfc_emite_json_a_stdout() -> None:
    """Principio 2: toda salida es JSON; no hay texto libre."""
    result = runner.invoke(app, ["rfc", "AAA010101AAA"])
    # Debe poder parsearse como JSON sin excepciones
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert "rfc" in data
    assert "valido" in data


def test_rfc_invalido_no_incluye_tipo() -> None:
    """Un RFC inválido no debe incluir el campo tipo en la salida JSON."""
    result = runner.invoke(app, ["rfc", "AAA"])
    data = json.loads(result.output)
    assert "tipo" not in data


def test_rfc_valido_no_incluye_motivo() -> None:
    """Un RFC válido no debe incluir el campo motivo en la salida JSON."""
    result = runner.invoke(app, ["rfc", "AAA010101AAA"])
    data = json.loads(result.output)
    assert "motivo" not in data

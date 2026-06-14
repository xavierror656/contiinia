"""Pruebas de integración para `contiinia version` via CliRunner."""

import json

from typer.testing import CliRunner

from contiinia.cli import app

runner = CliRunner()


def test_version_exit_code_cero() -> None:
    """CA-VER-01: `contiinia version` sale con exit code 0."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0, f"stderr/output: {result.output}"


def test_version_emite_json_valido() -> None:
    """CA-VER-02: `contiinia version` emite JSON válido a stdout."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)


def test_version_contiene_campo_version() -> None:
    """CA-VER-02: la salida JSON contiene el campo 'version'."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "version" in data


def test_version_contiene_campo_python() -> None:
    """CA-VER-02: la salida JSON contiene el campo 'python'."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "python" in data


def test_version_contiene_campo_platform() -> None:
    """CA-VER-02: la salida JSON contiene el campo 'platform'."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "platform" in data


def test_version_semver() -> None:
    """CA-VER-03: el campo 'version' tiene formato semver (X.Y.Z)."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    partes = data["version"].split(".")
    assert len(partes) == 3
    for parte in partes:
        assert parte.isdigit()


def test_version_schema() -> None:
    """CA-VER-04: `contiinia version --schema` emite JSON Schema válido."""
    result = runner.invoke(app, ["version", "--schema"])
    assert result.exit_code == 0
    schema = json.loads(result.output)
    assert "properties" in schema or "title" in schema

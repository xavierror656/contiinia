"""Pruebas unitarias para VersionInfo y el comando version."""

import json

import pytest

from contiinia.models.version import VersionInfo


def test_version_info_defaults() -> None:
    """VersionInfo tiene los valores por defecto correctos."""
    info = VersionInfo()
    assert info.cli == "contiinia"
    assert info.version == "1.3.0"
    assert info.cfdi_soportados == ["4.0"]
    assert info.spec_version == "1.2"


def test_version_info_json_valido() -> None:
    """VersionInfo serializa a JSON válido con campo 'version'."""
    info = VersionInfo()
    data = json.loads(info.model_dump_json())
    assert "version" in data
    assert data["version"] == "1.3.0"


def test_version_info_cfdi_soportados() -> None:
    """cfdi_soportados contiene al menos '4.0'."""
    info = VersionInfo()
    assert "4.0" in info.cfdi_soportados


def test_version_info_semver() -> None:
    """El campo version tiene formato semver (X.Y.Z)."""
    info = VersionInfo()
    partes = info.version.split(".")
    assert len(partes) == 3
    for parte in partes:
        assert parte.isdigit(), f"Parte no numérica en semver: {parte!r}"

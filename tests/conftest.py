"""Configuración de pytest — fixtures de rutas y helpers."""

from pathlib import Path

import pytest

# Ruta absoluta al directorio fixtures/ en la raíz del proyecto.
FIXTURES_DIR: Path = Path(__file__).parent.parent / "fixtures"


def fixture_path(nombre: str) -> Path:
    """Devuelve la ruta absoluta a un fixture sintético por nombre."""
    return FIXTURES_DIR / nombre


@pytest.fixture
def fixtures_dir() -> Path:
    """Fixture pytest que expone el directorio de fixtures sintéticos."""
    return FIXTURES_DIR

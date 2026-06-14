"""Pruebas unitarias para parsear_lote y detectar_duplicados — Hito 4.6."""

from pathlib import Path

import pytest

from contiinia.errors import DirectorioNoEncontradoError
from contiinia.parsers.lote import detectar_duplicados, parsear_lote

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# parsear_lote
# ---------------------------------------------------------------------------


def test_parsear_lote_total_archivos(fixtures_dir: Path) -> None:
    """parsear_lote() procesa todos los XML del directorio."""
    result = parsear_lote(fixtures_dir)
    assert result.total_archivos >= 5


def test_parsear_lote_exitosos(fixtures_dir: Path) -> None:
    """parsear_lote() tiene al menos 3 exitosos (CFDI 4.0 válidos)."""
    result = parsear_lote(fixtures_dir)
    assert result.exitosos >= 3


def test_parsear_lote_items_con_error(fixtures_dir: Path) -> None:
    """Los archivos con error (3.3, corrupto) tienen estado='error' y error no nulo."""
    result = parsear_lote(fixtures_dir)
    errores = [r for r in result.resultados if r.estado == "error"]
    assert len(errores) >= 1
    for item in errores:
        assert item.error is not None
        assert item.error.detalle


def test_parsear_lote_exitosos_sin_error(fixtures_dir: Path) -> None:
    """Los items exitosos tienen estado='ok', datos no nulos y error=None."""
    result = parsear_lote(fixtures_dir)
    exitosos = [r for r in result.resultados if r.estado == "ok"]
    for item in exitosos:
        assert item.datos is not None
        assert item.error is None


def test_parsear_lote_conteo_consistente(fixtures_dir: Path) -> None:
    """exitosos + errores == total_archivos."""
    result = parsear_lote(fixtures_dir)
    assert result.exitosos + result.errores == result.total_archivos


def test_parsear_lote_directorio_no_existe() -> None:
    """Directorio no existente lanza DirectorioNoEncontradoError."""
    with pytest.raises(DirectorioNoEncontradoError):
        parsear_lote(Path("/tmp/directorio_que_no_existe_contiinia_xyz"))


def test_parsear_lote_no_recursivo_excluye_subdirs(tmp_path: Path) -> None:
    """Sin --recursivo los subdirectorios son ignorados."""
    subdir = tmp_path / "sub"
    subdir.mkdir()
    # Copiar un XML al subdirectorio
    xml_src = FIXTURES_DIR / "cfdi_ingreso.xml"
    (subdir / "cfdi_ingreso.xml").write_bytes(xml_src.read_bytes())
    result = parsear_lote(tmp_path, recursivo=False)
    assert result.total_archivos == 0


def test_parsear_lote_recursivo_incluye_subdirs(tmp_path: Path) -> None:
    """Con --recursivo los subdirectorios se incluyen."""
    subdir = tmp_path / "sub"
    subdir.mkdir()
    xml_src = FIXTURES_DIR / "cfdi_ingreso.xml"
    (subdir / "cfdi_ingreso.xml").write_bytes(xml_src.read_bytes())
    result = parsear_lote(tmp_path, recursivo=True)
    assert result.total_archivos == 1
    assert result.exitosos == 1


def test_parsear_lote_directorio_vacio(tmp_path: Path) -> None:
    """Directorio vacío → total_archivos=0, exit implícito 0."""
    result = parsear_lote(tmp_path)
    assert result.total_archivos == 0
    assert result.exitosos == 0
    assert result.errores == 0


def test_parsear_lote_recursivo_flag(fixtures_dir: Path) -> None:
    """El campo recursivo se refleja correctamente en LoteResult."""
    r_false = parsear_lote(fixtures_dir, recursivo=False)
    assert r_false.recursivo is False
    r_true = parsear_lote(fixtures_dir, recursivo=True)
    assert r_true.recursivo is True


# ---------------------------------------------------------------------------
# detectar_duplicados
# ---------------------------------------------------------------------------


def test_detectar_duplicados_encuentra_duplicado(fixtures_dir: Path) -> None:
    """cfdi_duplicado.xml y cfdi_ingreso.xml tienen el mismo UUID; se detectan."""
    result = detectar_duplicados(fixtures_dir)
    assert result.total_duplicados >= 1
    uuids_dup = [d.uuid for d in result.duplicados]
    # El UUID compartido está en ambos fixtures
    assert any("12345678-1234-1234-1234-123456789001" in u for u in uuids_dup)


def test_detectar_duplicados_ocurrencias(fixtures_dir: Path) -> None:
    """El duplicado encontrado tiene ocurrencias >= 2 y al menos 2 archivos."""
    result = detectar_duplicados(fixtures_dir)
    for dup in result.duplicados:
        assert dup.ocurrencias >= 2
        assert len(dup.archivos) >= 2
        assert dup.ocurrencias == len(dup.archivos)


def test_detectar_duplicados_uuid_mayusculas(fixtures_dir: Path) -> None:
    """Los UUIDs en duplicados están normalizados a mayúsculas (CA-DUP-05)."""
    result = detectar_duplicados(fixtures_dir)
    for dup in result.duplicados:
        assert dup.uuid == dup.uuid.upper()


def test_detectar_duplicados_advertencias_por_corrupto(fixtures_dir: Path) -> None:
    """cfdi_xml_corrupto.xml genera una advertencia, no detiene el proceso (CA-DUP-04)."""
    result = detectar_duplicados(fixtures_dir)
    motivos = [a.motivo for a in result.advertencias]
    assert len(result.advertencias) >= 1
    assert any(m in ("xml_malformado", "version_no_soportada") for m in motivos)


def test_detectar_duplicados_directorio_no_existe() -> None:
    """Directorio no existente lanza DirectorioNoEncontradoError (CA-DUP-06)."""
    with pytest.raises(DirectorioNoEncontradoError):
        detectar_duplicados(Path("/tmp/directorio_que_no_existe_contiinia_xyz"))


def test_detectar_duplicados_sin_duplicados(tmp_path: Path) -> None:
    """Directorio con un solo XML → duplicados vacío (CA-DUP-01)."""
    xml_src = FIXTURES_DIR / "cfdi_ingreso.xml"
    (tmp_path / "cfdi_ingreso.xml").write_bytes(xml_src.read_bytes())
    result = detectar_duplicados(tmp_path)
    assert result.total_duplicados == 0
    assert result.duplicados == []

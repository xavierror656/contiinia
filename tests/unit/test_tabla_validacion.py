"""Pruebas adversariales para Feature 2: validación cruzada de importes.

Cubre CA-TAB-16..21.
Usa io.StringIO (CSV en memoria) vía NamedTemporaryFile para rapidez.
"""

from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

import pytest

from contiinia.models.tabla import AdvertenciaImporteInconsistente, AdvertenciaTasaNoNumerica
from contiinia.parsers.tabla import parsear_tabla


def _csv_to_path(contenido: str, tmp_path: Path, nombre: str = "tabla.csv") -> Path:
    """Escribe el contenido CSV a un archivo temporal y devuelve el Path."""
    ruta = tmp_path / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


# ---------------------------------------------------------------------------
# CA-TAB-16: diferencia 0 → sin advertencia
# ---------------------------------------------------------------------------


def test_importe_exacto_sin_advertencia(tmp_path: Path) -> None:
    """CA-TAB-16: cantidad=2, VU=5000, importe=10000 → diferencia 0, sin advertencia."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,2.000000,5000.00,10000.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    inconsistencias = [
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    ]
    assert inconsistencias == [], f"No esperaba advertencias, obtuve: {inconsistencias}"


def test_importe_exacto_exit_no_lanza(tmp_path: Path) -> None:
    """CA-TAB-16: importe exacto → no lanza excepción."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,2.000000,5000.00,10000.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    assert result.total_registros == 1


# ---------------------------------------------------------------------------
# CA-TAB-17: diferencia 500 > 0.01 → advertencia importe_inconsistente
# ---------------------------------------------------------------------------


def test_importe_inconsistente_genera_advertencia(tmp_path: Path) -> None:
    """CA-TAB-17: cantidad=2, VU=5000, importe=10500 → advertencia tipo importe_inconsistente."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,2.000000,5000.00,10500.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    inconsistencias = [
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    ]
    assert len(inconsistencias) == 1


def test_importe_inconsistente_fila_correcta(tmp_path: Path) -> None:
    """CA-TAB-17: la advertencia tiene fila=2 (primera fila de datos)."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,2.000000,5000.00,10500.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    adv = next(
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    )
    assert adv.fila == 2


def test_importe_inconsistente_importe_declarado(tmp_path: Path) -> None:
    """CA-TAB-17: importe_declarado en advertencia es '10500.00'."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,2.000000,5000.00,10500.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    adv = next(
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    )
    assert adv.importe_declarado == "10500.00"


def test_importe_inconsistente_importe_calculado(tmp_path: Path) -> None:
    """CA-TAB-17: importe_calculado en advertencia es '10000.00'."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,2.000000,5000.00,10500.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    adv = next(
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    )
    assert adv.importe_calculado == "10000.00"


def test_importe_inconsistente_diferencia(tmp_path: Path) -> None:
    """CA-TAB-17: diferencia en advertencia es '500.00'."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,2.000000,5000.00,10500.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    adv = next(
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    )
    assert adv.diferencia == "500.00"


def test_importe_inconsistente_no_cambia_exit_code(tmp_path: Path) -> None:
    """CA-TAB-17: advertencia de importe inconsistente NO lanza excepción (exit no cambia)."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,2.000000,5000.00,10500.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    # No debe levantar excepción
    result = parsear_tabla(ruta)
    assert result.total_registros == 1
    # El registro de importe sigue siendo el declarado, no el calculado
    assert result.registros[0].importe is not None
    from decimal import Decimal
    assert result.registros[0].importe == Decimal("10500.00")


# ---------------------------------------------------------------------------
# CA-TAB-18: diferencia 0.005 ≤ 0.01 → dentro de tolerancia, sin advertencia
# ---------------------------------------------------------------------------


def test_diferencia_dentro_tolerancia_sin_advertencia(tmp_path: Path) -> None:
    """CA-TAB-18: cantidad=1, VU=100, importe=100.005 → |diff|=0.005≤0.01, sin advertencia."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,1.000000,100.00,100.005\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    inconsistencias = [
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    ]
    assert inconsistencias == [], f"No esperaba advertencias para diff=0.005, obtuve: {inconsistencias}"


def test_diferencia_001_exacta_sin_advertencia(tmp_path: Path) -> None:
    """CA-TAB-18: diferencia exactamente 0.01 → sin advertencia (≤ tolerancia)."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,1.000000,100.00,100.01\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    inconsistencias = [
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    ]
    assert inconsistencias == [], f"Diff=0.01 es tolerado pero se generó advertencia: {inconsistencias}"


def test_diferencia_002_supera_tolerancia_con_advertencia(tmp_path: Path) -> None:
    """CA-TAB-18 adversarial: cantidad=1, VU=100, importe=100.02 → diff=0.02>0.01, con advertencia."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,1.000000,100.00,100.02\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    inconsistencias = [
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    ]
    assert len(inconsistencias) == 1, f"Esperaba 1 advertencia para diff=0.02, obtuve: {inconsistencias}"


# ---------------------------------------------------------------------------
# CA-TAB-19: fila sin cantidad → no se valida cruzado
# ---------------------------------------------------------------------------


def test_fila_sin_cantidad_no_genera_advertencia(tmp_path: Path) -> None:
    """CA-TAB-19: fila donde cantidad está ausente → no genera advertencia importe_inconsistente."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,,5000.00,10000.00\n"  # cantidad vacía
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    inconsistencias = [
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    ]
    assert inconsistencias == []


def test_fila_sin_valor_unitario_no_genera_advertencia(tmp_path: Path) -> None:
    """CA-TAB-19 ext: fila donde valor_unitario está ausente → no genera advertencia."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,2.000000,,10000.00\n"  # VU vacío
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    inconsistencias = [
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    ]
    assert inconsistencias == []


def test_fila_sin_importe_no_genera_advertencia(tmp_path: Path) -> None:
    """CA-TAB-19 ext: fila donde importe está ausente → no genera advertencia."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,2.000000,5000.00,\n"  # importe vacío
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    inconsistencias = [
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    ]
    assert inconsistencias == []


# ---------------------------------------------------------------------------
# CA-TAB-20: 5 filas, 3 inconsistentes → exactamente 3 advertencias
# ---------------------------------------------------------------------------


def test_cinco_filas_tres_inconsistentes(tmp_path: Path) -> None:
    """CA-TAB-20: 5 filas con 3 inconsistencias → exactamente 3 objetos importe_inconsistente."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,OK_1,2.000000,5000.00,10000.00\n"          # correcto
        "84111507,INCONSISTENTE_1,2.000000,5000.00,10500.00\n"  # diff=500
        "84111508,OK_2,1.000000,100.00,100.00\n"              # correcto
        "84111509,INCONSISTENTE_2,1.000000,100.00,200.00\n"   # diff=100
        "84111510,INCONSISTENTE_3,3.000000,100.00,400.00\n"   # diff=100
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    inconsistencias = [
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    ]
    assert len(inconsistencias) == 3, f"Esperaba 3 advertencias, obtuve: {len(inconsistencias)}"


def test_cinco_filas_tres_inconsistentes_exit_0(tmp_path: Path) -> None:
    """CA-TAB-20: 3 inconsistencias → no lanza excepción (exit implícito 0)."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,OK_1,2.000000,5000.00,10000.00\n"
        "84111507,INCONSISTENTE_1,2.000000,5000.00,10500.00\n"
        "84111508,OK_2,1.000000,100.00,100.00\n"
        "84111509,INCONSISTENTE_2,1.000000,100.00,200.00\n"
        "84111510,INCONSISTENTE_3,3.000000,100.00,400.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    assert result.total_registros == 5


# ---------------------------------------------------------------------------
# CA-TAB-21: importe_declarado, importe_calculado, diferencia son strings
# ---------------------------------------------------------------------------


def test_advertencia_campos_son_strings_no_numeros(tmp_path: Path) -> None:
    """CA-TAB-21: importe_declarado, importe_calculado y diferencia son strings, no numbers JSON."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,2.000000,5000.00,10500.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    # Serializar a JSON y re-parsear para verificar tipos nativos JSON
    data = json.loads(result.model_dump_json())
    adv = next(
        a for a in data["advertencias"]
        if isinstance(a, dict) and a.get("tipo") == "importe_inconsistente"
    )
    assert isinstance(adv["importe_declarado"], str), f"importe_declarado debe ser str: {type(adv['importe_declarado'])}"
    assert isinstance(adv["importe_calculado"], str), f"importe_calculado debe ser str: {type(adv['importe_calculado'])}"
    assert isinstance(adv["diferencia"], str), f"diferencia debe ser str: {type(adv['diferencia'])}"


def test_advertencia_campos_no_son_float(tmp_path: Path) -> None:
    """CA-TAB-21: ningún campo de advertencia es float en JSON serializado."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,2.000000,5000.00,10500.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    data = json.loads(result.model_dump_json())
    for adv in data["advertencias"]:
        if isinstance(adv, dict) and adv.get("tipo") == "importe_inconsistente":
            assert not isinstance(adv["importe_declarado"], float)
            assert not isinstance(adv["importe_calculado"], float)
            assert not isinstance(adv["diferencia"], float)


# ---------------------------------------------------------------------------
# Adversarial: diferencia negativa también detectada (importe < esperado)
# ---------------------------------------------------------------------------


def test_importe_menor_que_esperado_genera_advertencia(tmp_path: Path) -> None:
    """Adversarial: importe=9000 < esperado=10000 → diferencia=1000 > 0.01, con advertencia."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,2.000000,5000.00,9000.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    inconsistencias = [
        a for a in result.advertencias
        if isinstance(a, AdvertenciaImporteInconsistente)
    ]
    assert len(inconsistencias) == 1
    # diferencia es valor absoluto
    assert inconsistencias[0].diferencia == "1000.00"


# ---------------------------------------------------------------------------
# Adversarial: columna cantidad ausente en el archivo (no en la fila)
# ---------------------------------------------------------------------------


def test_columna_cantidad_ausente_no_genera_advertencia(tmp_path: Path) -> None:
    """CA-TAB-19 columna total ausente: si la columna 'cantidad' no existe en el archivo,
    no hay validación cruzada en ninguna fila."""
    # Archivo sin columna cantidad
    csv = (
        "clave_prod_serv,descripcion,valor_unitario,importe\n"
        "84111506,Servicio,5000.00,10500.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    # Esto lanzará ColumnaRequeridaAusenteError porque cantidad es requerida
    from contiinia.errors import ColumnaRequeridaAusenteError
    with pytest.raises(ColumnaRequeridaAusenteError):
        parsear_tabla(ruta)

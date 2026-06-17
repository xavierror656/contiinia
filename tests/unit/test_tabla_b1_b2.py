"""Pruebas unitarias para extensiones B1 (factura completa) y B2 (nómina CONTPAQi)."""

from __future__ import annotations

import csv
import tempfile
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest

from contiinia.errors import ValorNoNumericoError
from contiinia.parsers.tabla import parsear_tabla

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"
CONTPAQI = FIXTURES / "tabla_contpaqi"


def _csv_tmpfile(rows: list[list[str]]) -> Path:
    """Crea un CSV temporal y retorna su Path."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as tmp:
        writer = csv.writer(tmp)
        for row in rows:
            writer.writerow(row)
        return Path(tmp.name)


def _xlsx_tmpfile(rows: list[list[str]]) -> Path:
    """Crea un XLSX temporal y retorna su Path."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    for row in rows:
        ws.append(row)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        name = tmp.name
    wb.save(name)
    return Path(name)


# ---------------------------------------------------------------------------
# CA-TAB-B1-01 / B1-06
# ---------------------------------------------------------------------------


def test_descuento_presente() -> None:
    """Columna Descuento → campo descuento en cada fila como string decimal."""
    ruta = _csv_tmpfile([
        ["ClaveProdServ", "Descripcion", "Cantidad", "ValorUnitario", "Descuento", "Importe"],
        ["84111506", "Servicio A", "1", "100.00", "10.00", "90.00"],
        ["84111507", "Servicio B", "2", "50.00",  "5.00",  "95.00"],
    ])
    result = parsear_tabla(ruta)
    assert result.registros[0].descuento == Decimal("10.00")
    assert result.registros[1].descuento == Decimal("5.00")
    # serialización como string
    dumped = result.registros[0].model_dump(exclude_none=True)
    assert isinstance(dumped["descuento"], str)
    assert dumped["descuento"] == "10.00"


def test_descuento_vacio() -> None:
    """Celda Descuento vacía → campo descuento omitido (None → excluido con exclude_none)."""
    ruta = _csv_tmpfile([
        ["ClaveProdServ", "Descripcion", "Cantidad", "ValorUnitario", "Descuento", "Importe"],
        ["84111506", "Servicio A", "1", "100.00", "", "100.00"],
    ])
    result = parsear_tabla(ruta)
    assert result.registros[0].descuento is None
    dumped = result.registros[0].model_dump(exclude_none=True)
    assert "descuento" not in dumped


def test_descuento_no_numerico() -> None:
    """Valor no numérico en Descuento (e.g. 'N/A') → ValorNoNumericoError (exit 1)."""
    ruta = _csv_tmpfile([
        ["ClaveProdServ", "Descripcion", "Cantidad", "ValorUnitario", "Descuento", "Importe"],
        ["84111506", "Servicio A", "1", "100.00", "N/A", "100.00"],
    ])
    with pytest.raises(ValorNoNumericoError):
        parsear_tabla(ruta)


# ---------------------------------------------------------------------------
# CA-TAB-B1-02
# ---------------------------------------------------------------------------


def test_clave_unidad_alias() -> None:
    """Columna ClaveUnidad (camelCase de CONTPAQi) → clave_unidad en JSON."""
    ruta = _csv_tmpfile([
        ["ClaveProdServ", "Descripcion", "Cantidad", "ValorUnitario", "Importe", "ClaveUnidad"],
        ["84111506", "Servicio A", "1", "100.00", "100.00", "E48"],
        ["84111507", "Servicio B", "2", "50.00",  "100.00", "H87"],
    ])
    result = parsear_tabla(ruta)
    assert "clave_unidad" in result.columnas_detectadas
    assert result.registros[0].clave_unidad == "E48"
    assert result.registros[1].clave_unidad == "H87"


# ---------------------------------------------------------------------------
# CA-TAB-B1-03
# ---------------------------------------------------------------------------


def test_no_identificacion_sku() -> None:
    """Columna SKU → no_identificacion en JSON."""
    ruta = _csv_tmpfile([
        ["ClaveProdServ", "Descripcion", "Cantidad", "ValorUnitario", "Importe", "SKU"],
        ["84111506", "Servicio A", "1", "100.00", "100.00", "SKU-001"],
    ])
    result = parsear_tabla(ruta)
    assert "no_identificacion" in result.columnas_detectadas
    assert result.registros[0].no_identificacion == "SKU-001"


# ---------------------------------------------------------------------------
# CA-TAB-B2-01
# ---------------------------------------------------------------------------


def test_tipo_nomina() -> None:
    """Columna Tipo con 'P' y 'D' → tipo_nomina en JSON."""
    headers = ["Clave", "Tipo", "Descripcion", "Cantidad", "ValorUnitario", "Importe",
               "Gravado", "Exento"]
    ruta = _csv_tmpfile([
        headers,
        ["001", "P", "Sueldo", "1", "15000.00", "15000.00", "12000.00", "3000.00"],
        ["001", "D", "ISR",    "1",  "2400.00",  "2400.00",  "2400.00",    "0.00"],
    ])
    result = parsear_tabla(ruta)
    assert result.registros[0].tipo_nomina == "P"
    assert result.registros[1].tipo_nomina == "D"
    assert "tipo_nomina" in result.columnas_detectadas


# ---------------------------------------------------------------------------
# CA-TAB-B2-02 / B2-03 / B2-08
# ---------------------------------------------------------------------------


def test_gravado_exento() -> None:
    """Columnas Gravado y Exento → string decimales en JSON (nunca number)."""
    ruta = _csv_tmpfile([
        ["Clave", "Descripcion", "Cantidad", "ValorUnitario", "Importe", "Gravado", "Exento"],
        ["001", "Sueldo", "1", "15000.00", "15000.00", "12000.00", "3000.00"],
    ])
    result = parsear_tabla(ruta)
    row = result.registros[0]
    assert row.gravado == Decimal("12000.00")
    assert row.exento == Decimal("3000.00")
    dumped = row.model_dump(exclude_none=True)
    assert isinstance(dumped["gravado"], str)
    assert isinstance(dumped["exento"], str)
    assert dumped["gravado"] == "12000.00"
    assert dumped["exento"] == "3000.00"


# ---------------------------------------------------------------------------
# CA-TAB-B2-06
# ---------------------------------------------------------------------------


def test_nomina_sin_columnas_extra() -> None:
    """Archivo nómina CONTPAQi completo → columnas_extra: {} en todas las filas."""
    result = parsear_tabla(CONTPAQI / "nomina_conceptos.xlsx")
    for row in result.registros:
        assert row.columnas_extra == {}, (
            f"Fila {row.fila} tiene columnas_extra: {row.columnas_extra}"
        )


# ---------------------------------------------------------------------------
# CA-TAB-B1-04 / B2-04 — compatibilidad hacia atrás
# ---------------------------------------------------------------------------


def test_sin_columnas_b1_b2_no_afecta_salida() -> None:
    """Archivo sin columnas B1/B2 → sin nuevos campos en JSON (compatibilidad)."""
    ruta = _csv_tmpfile([
        ["ClaveProdServ", "Descripcion", "Cantidad", "ValorUnitario", "Importe"],
        ["84111506", "Servicio A", "1", "100.00", "100.00"],
    ])
    result = parsear_tabla(ruta)
    row = result.registros[0]
    dumped = row.model_dump(exclude_none=True)
    campos_b1_b2 = ("descuento", "clave_unidad", "no_identificacion",
                    "tipo_nomina", "gravado", "exento")
    for campo in campos_b1_b2:
        assert campo not in dumped, f"Campo {campo} no debería estar presente"


# ---------------------------------------------------------------------------
# CA-TAB-B2-09
# ---------------------------------------------------------------------------


def test_coexistencia_b1_b2() -> None:
    """Columnas B1+B2 juntas → todos los campos mapeados, sin columnas_extra."""
    ruta = _xlsx_tmpfile([
        [
            "ClaveProdServ", "Descripcion", "Cantidad", "ValorUnitario",
            "Descuento", "Importe", "ClaveUnidad", "NoIdentificacion",
            "Tipo", "Gravado", "Exento",
        ],
        [
            "84111506", "Servicio integral", "1", "10000.00",
            "500.00", "9500.00", "E48", "SKU-999",
            "P", "8000.00", "1500.00",
        ],
    ])
    result = parsear_tabla(ruta)
    row = result.registros[0]
    assert row.descuento == Decimal("500.00")
    assert row.clave_unidad == "E48"
    assert row.no_identificacion == "SKU-999"
    assert row.tipo_nomina == "P"
    assert row.gravado == Decimal("8000.00")
    assert row.exento == Decimal("1500.00")
    assert row.columnas_extra == {}


# ---------------------------------------------------------------------------
# Fixture XLSX — factura_completa_descuento.xlsx
# ---------------------------------------------------------------------------


def test_fixture_factura_completa_descuento_columnas_extra_vacias() -> None:
    """factura_completa_descuento.xlsx → columnas_extra: {} en todas las filas."""
    result = parsear_tabla(CONTPAQI / "factura_completa_descuento.xlsx")
    for row in result.registros:
        assert row.columnas_extra == {}, (
            f"Fila {row.fila} tiene columnas_extra: {row.columnas_extra}"
        )


def test_fixture_factura_completa_descuento_descuento_vacio_omitido() -> None:
    """Filas con Descuento vacío en fixture → descuento omitido (None)."""
    result = parsear_tabla(CONTPAQI / "factura_completa_descuento.xlsx")
    # Filas 4 y 5 (índice 2 y 3, fila=4 y fila=5) tienen Descuento vacío
    filas_con_descuento_vacio = [r for r in result.registros if r.descuento is None]
    assert len(filas_con_descuento_vacio) >= 2

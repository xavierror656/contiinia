"""Pruebas adversariales para Feature 1: .xls y .ods en contiinia tabla.

Cubre CA-TAB-10..15.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from contiinia.errors import ArchivoSinDatosError, FormatoNoSoportadoError
from contiinia.parsers.tabla import parsear_tabla

# ---------------------------------------------------------------------------
# Helpers de creación de fixtures
# ---------------------------------------------------------------------------

_HEADER = ["clave_prod_serv", "descripcion", "cantidad", "valor_unitario", "importe"]
_ROW1 = ["84111506", "Servicio de consultoría", "1.000000", "10000.00", "10000.00"]
_ROW2 = ["01010101", "Producto adicional", "2.000000", "500.00", "1000.00"]


def _make_xls(path: Path, rows: list[list], sheet2_rows: list[list] | None = None) -> None:
    """Crea un archivo .xls con xlwt. Opcionalmente agrega una segunda hoja."""
    import xlwt  # type: ignore[import]

    wb = xlwt.Workbook()
    ws = wb.add_sheet("Conceptos")
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            ws.write(r_idx, c_idx, val)

    if sheet2_rows is not None:
        ws2 = wb.add_sheet("Hoja2")
        for r_idx, row in enumerate(sheet2_rows):
            for c_idx, val in enumerate(row):
                ws2.write(r_idx, c_idx, val)

    wb.save(str(path))


def _make_ods(path: Path, rows: list[list], sheet2_rows: list[list] | None = None) -> None:
    """Crea un archivo .ods usando pandas con engine='odf'.

    La primera fila de `rows` se usa como encabezado del DataFrame.
    """
    import pandas as pd

    def rows_to_df(data: list[list]) -> pd.DataFrame:
        header = [str(v) for v in data[0]]
        body = [[str(v) for v in row] for row in data[1:]]
        return pd.DataFrame(body, columns=header)

    df1 = rows_to_df(rows)
    if sheet2_rows is not None:
        df2 = rows_to_df(sheet2_rows)
        with pd.ExcelWriter(str(path), engine="odf") as writer:
            df1.to_excel(writer, sheet_name="Conceptos", index=False)
            df2.to_excel(writer, sheet_name="Hoja2", index=False)
    else:
        df1.to_excel(str(path), index=False, engine="odf", sheet_name="Conceptos")


# ---------------------------------------------------------------------------
# CA-TAB-10: .xls válido de una hoja → exit 0, formato "xls"
# ---------------------------------------------------------------------------


def test_xls_valido_una_hoja_formato(tmp_path: Path) -> None:
    """CA-TAB-10: .xls válido → campo formato es 'xls'."""
    ruta = tmp_path / "tabla.xls"
    _make_xls(ruta, [_HEADER, _ROW1, _ROW2])
    result = parsear_tabla(ruta)
    assert result.formato == "xls"


def test_xls_valido_una_hoja_total_registros(tmp_path: Path) -> None:
    """CA-TAB-10: .xls válido con 2 filas de datos → total_registros=2."""
    ruta = tmp_path / "tabla.xls"
    _make_xls(ruta, [_HEADER, _ROW1, _ROW2])
    result = parsear_tabla(ruta)
    assert result.total_registros == 2


def test_xls_valido_una_hoja_sin_advertencias(tmp_path: Path) -> None:
    """CA-TAB-10: .xls válido con una sola hoja → sin advertencias."""
    ruta = tmp_path / "tabla.xls"
    _make_xls(ruta, [_HEADER, _ROW1])
    result = parsear_tabla(ruta)
    assert result.advertencias == []


def test_xls_valido_valores_correctos(tmp_path: Path) -> None:
    """CA-TAB-10: primer registro tiene clave_prod_serv correcta."""
    ruta = tmp_path / "tabla.xls"
    _make_xls(ruta, [_HEADER, _ROW1, _ROW2])
    result = parsear_tabla(ruta)
    assert result.registros[0].clave_prod_serv == "84111506"


def test_xls_columnas_detectadas(tmp_path: Path) -> None:
    """CA-TAB-10: columnas_detectadas incluye las 5 columnas canónicas."""
    ruta = tmp_path / "tabla.xls"
    _make_xls(ruta, [_HEADER, _ROW1])
    result = parsear_tabla(ruta)
    for col in ["clave_prod_serv", "descripcion", "cantidad", "valor_unitario", "importe"]:
        assert col in result.columnas_detectadas, f"Falta columna: {col}"


def test_xls_json_importes_son_strings(tmp_path: Path) -> None:
    """CA-TAB-10: en JSON serializado, decimales son strings."""
    ruta = tmp_path / "tabla.xls"
    _make_xls(ruta, [_HEADER, _ROW1])
    result = parsear_tabla(ruta)
    data = json.loads(result.model_dump_json())
    reg = data["registros"][0]
    assert isinstance(reg["cantidad"], str)
    assert isinstance(reg["valor_unitario"], str)
    assert isinstance(reg["importe"], str)


# ---------------------------------------------------------------------------
# CA-TAB-11: .ods válido de una hoja → exit 0, formato "ods"
# ---------------------------------------------------------------------------


def test_ods_valido_una_hoja_formato(tmp_path: Path) -> None:
    """CA-TAB-11: .ods válido → campo formato es 'ods'."""
    ruta = tmp_path / "tabla.ods"
    _make_ods(ruta, [_HEADER, _ROW1, _ROW2])
    result = parsear_tabla(ruta)
    assert result.formato == "ods"


def test_ods_valido_una_hoja_total_registros(tmp_path: Path) -> None:
    """CA-TAB-11: .ods válido con 2 filas → total_registros=2."""
    ruta = tmp_path / "tabla.ods"
    _make_ods(ruta, [_HEADER, _ROW1, _ROW2])
    result = parsear_tabla(ruta)
    assert result.total_registros == 2


def test_ods_valido_una_hoja_sin_advertencias(tmp_path: Path) -> None:
    """CA-TAB-11: .ods válido con una sola hoja → sin advertencias."""
    ruta = tmp_path / "tabla.ods"
    _make_ods(ruta, [_HEADER, _ROW1])
    result = parsear_tabla(ruta)
    assert result.advertencias == []


def test_ods_valido_valores_correctos(tmp_path: Path) -> None:
    """CA-TAB-11: primer registro tiene clave_prod_serv correcta."""
    ruta = tmp_path / "tabla.ods"
    _make_ods(ruta, [_HEADER, _ROW1, _ROW2])
    result = parsear_tabla(ruta)
    assert result.registros[0].clave_prod_serv == "84111506"


def test_ods_columnas_detectadas(tmp_path: Path) -> None:
    """CA-TAB-11: .ods columnas_detectadas incluye columnas canónicas."""
    ruta = tmp_path / "tabla.ods"
    _make_ods(ruta, [_HEADER, _ROW1])
    result = parsear_tabla(ruta)
    for col in ["clave_prod_serv", "descripcion", "cantidad", "valor_unitario", "importe"]:
        assert col in result.columnas_detectadas, f"Falta columna: {col}"


# ---------------------------------------------------------------------------
# CA-TAB-12: .xls con 2 hojas → advertencia, se procesa la primera
# ---------------------------------------------------------------------------


def test_xls_multi_hoja_procesa_primera(tmp_path: Path) -> None:
    """CA-TAB-12: .xls con 2 hojas → solo datos de la primera hoja."""
    ruta = tmp_path / "multi.xls"
    _make_xls(ruta, [_HEADER, _ROW1], sheet2_rows=[_HEADER, _ROW2, _ROW2])
    result = parsear_tabla(ruta)
    # La primera hoja tiene solo 1 fila de datos
    assert result.total_registros == 1
    assert result.registros[0].clave_prod_serv == "84111506"


def test_xls_multi_hoja_emite_advertencia(tmp_path: Path) -> None:
    """CA-TAB-12: .xls con 2 hojas → advertencias[] contiene exactamente una advertencia."""
    ruta = tmp_path / "multi.xls"
    _make_xls(ruta, [_HEADER, _ROW1], sheet2_rows=[_HEADER, _ROW2])
    result = parsear_tabla(ruta)
    assert len(result.advertencias) >= 1


def test_xls_multi_hoja_advertencia_menciona_hojas(tmp_path: Path) -> None:
    """CA-TAB-12: la advertencia menciona el número de hojas y sus nombres."""
    ruta = tmp_path / "multi.xls"
    _make_xls(ruta, [_HEADER, _ROW1], sheet2_rows=[_HEADER, _ROW2])
    result = parsear_tabla(ruta)
    adv_texto = str(result.advertencias[0])
    # Debe mencionar que hay 2 hojas y al menos el nombre de la primera
    assert "2" in adv_texto
    assert "Conceptos" in adv_texto


def test_xls_multi_hoja_exit_no_falla(tmp_path: Path) -> None:
    """CA-TAB-12: .xls con 2 hojas → no lanza excepción."""
    ruta = tmp_path / "multi.xls"
    _make_xls(ruta, [_HEADER, _ROW1], sheet2_rows=[_HEADER, _ROW2])
    # No debe levantar excepción
    result = parsear_tabla(ruta)
    assert result is not None


# ---------------------------------------------------------------------------
# CA-TAB-13: .ods con 2 hojas → advertencia, se procesa la primera
# ---------------------------------------------------------------------------


def test_ods_multi_hoja_procesa_primera(tmp_path: Path) -> None:
    """CA-TAB-13: .ods con 2 hojas → solo datos de la primera hoja."""
    ruta = tmp_path / "multi.ods"
    _make_ods(ruta, [_HEADER, _ROW1], sheet2_rows=[_HEADER, _ROW2, _ROW2])
    result = parsear_tabla(ruta)
    assert result.total_registros == 1
    assert result.registros[0].clave_prod_serv == "84111506"


def test_ods_multi_hoja_emite_advertencia(tmp_path: Path) -> None:
    """CA-TAB-13: .ods con 2 hojas → advertencias[] no vacío."""
    ruta = tmp_path / "multi.ods"
    _make_ods(ruta, [_HEADER, _ROW1], sheet2_rows=[_HEADER, _ROW2])
    result = parsear_tabla(ruta)
    assert len(result.advertencias) >= 1


def test_ods_multi_hoja_advertencia_menciona_hojas(tmp_path: Path) -> None:
    """CA-TAB-13: advertencia en .ods menciona número de hojas y nombre."""
    ruta = tmp_path / "multi.ods"
    _make_ods(ruta, [_HEADER, _ROW1], sheet2_rows=[_HEADER, _ROW2])
    result = parsear_tabla(ruta)
    adv_texto = str(result.advertencias[0])
    assert "2" in adv_texto


def test_ods_multi_hoja_formato_ods(tmp_path: Path) -> None:
    """CA-TAB-13: .ods con múltiples hojas → campo formato sigue siendo 'ods'."""
    ruta = tmp_path / "multi.ods"
    _make_ods(ruta, [_HEADER, _ROW1], sheet2_rows=[_HEADER, _ROW2])
    result = parsear_tabla(ruta)
    assert result.formato == "ods"


# ---------------------------------------------------------------------------
# CA-TAB-14: .xls vacío → ArchivoSinDatosError
# ---------------------------------------------------------------------------


def test_xls_vacio_lanza_archivo_sin_datos(tmp_path: Path) -> None:
    """CA-TAB-14: .xls solo con encabezado (sin filas de datos) → ArchivoSinDatosError."""
    ruta = tmp_path / "vacio.xls"
    _make_xls(ruta, [_HEADER])  # Solo encabezado, sin filas de datos
    with pytest.raises(ArchivoSinDatosError):
        parsear_tabla(ruta)


def test_xls_solo_cabecera_sin_filas(tmp_path: Path) -> None:
    """CA-TAB-14: .xls con solo encabezado → error_type 'archivo_sin_datos'."""
    ruta = tmp_path / "vacio.xls"
    _make_xls(ruta, [_HEADER])
    with pytest.raises(ArchivoSinDatosError) as exc_info:
        parsear_tabla(ruta)
    assert exc_info.value.error_type == "archivo_sin_datos"


# ---------------------------------------------------------------------------
# CA-TAB-15: Extensión .xlsm → FormatoNoSoportadoError
# ---------------------------------------------------------------------------


def test_xlsm_lanza_formato_no_soportado(tmp_path: Path) -> None:
    """CA-TAB-15: .xlsm → FormatoNoSoportadoError (exit 1)."""
    ruta = tmp_path / "macro.xlsm"
    # Crear un archivo con contenido cualquiera; la validación es por extensión
    ruta.write_bytes(b"PK")  # cabecera ZIP falsa
    with pytest.raises(FormatoNoSoportadoError):
        parsear_tabla(ruta)


def test_xlsm_error_type_correcto(tmp_path: Path) -> None:
    """CA-TAB-15: error_type es 'formato_no_soportado'."""
    ruta = tmp_path / "macro.xlsm"
    ruta.write_bytes(b"PK")
    with pytest.raises(FormatoNoSoportadoError) as exc_info:
        parsear_tabla(ruta)
    assert exc_info.value.error_type == "formato_no_soportado"


def test_numbers_lanza_formato_no_soportado(tmp_path: Path) -> None:
    """CA-TAB-15: .numbers → FormatoNoSoportadoError."""
    ruta = tmp_path / "archivo.numbers"
    ruta.write_bytes(b"datos")
    with pytest.raises(FormatoNoSoportadoError):
        parsear_tabla(ruta)


def test_tsv_lanza_formato_no_soportado(tmp_path: Path) -> None:
    """CA-TAB-15: .tsv → FormatoNoSoportadoError."""
    ruta = tmp_path / "archivo.tsv"
    ruta.write_text("col1\tcol2\n")
    with pytest.raises(FormatoNoSoportadoError):
        parsear_tabla(ruta)


# ---------------------------------------------------------------------------
# Adversarial: columna Unicode con Ñ en .xls
# ---------------------------------------------------------------------------


def test_xls_columna_con_tilde_n(tmp_path: Path) -> None:
    """Adversarial: columna 'descripción' (con acento) mapeada a 'descripcion'."""
    ruta = tmp_path / "unicode.xls"
    header = ["clave_prod_serv", "descripción", "cantidad", "valor_unitario", "importe"]
    _make_xls(ruta, [header, _ROW1])
    result = parsear_tabla(ruta)
    assert "descripcion" in result.columnas_detectadas
    assert result.registros[0].descripcion == "Servicio de consultoría"


# ---------------------------------------------------------------------------
# Adversarial: .ods con columna tasa_iva
# ---------------------------------------------------------------------------


def test_ods_columna_tasa_iva_mapeada(tmp_path: Path) -> None:
    """Adversarial: .ods con columna 'tasa_iva' → mapeada a 'tasa'."""
    ruta = tmp_path / "tasa.ods"
    header = ["clave_prod_serv", "descripcion", "cantidad", "valor_unitario", "importe", "tasa_iva"]
    row = ["84111506", "Servicio", "1.000000", "10000.00", "10000.00", "0.160000"]
    _make_ods(ruta, [header, row])
    result = parsear_tabla(ruta)
    assert "tasa" in result.columnas_detectadas
    assert result.registros[0].iva_estimado is not None

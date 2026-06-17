"""Tests unitarios para aliases CONTPAQi en parsers/tabla.py."""

from __future__ import annotations

import tempfile
from decimal import Decimal
from pathlib import Path

from contiinia.parsers.tabla import _ALIAS_MAP, parsear_tabla

FIXTURES_CONTPAQI = Path(__file__).parent.parent.parent / "fixtures" / "tabla_contpaqi"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _csv_tmp(header: str, row: str) -> Path:
    """Crea un CSV temporal con una fila de datos y retorna su Path."""
    with tempfile.NamedTemporaryFile(
        suffix=".csv", mode="w", delete=False, encoding="utf-8"
    ) as f:
        f.write(header + "\n")
        f.write(row + "\n")
        return Path(f.name)


def _base_row_for(valor_unitario_col: str, importe_col: str = "importe") -> tuple[str, str]:
    """Genera header y fila CSV mínimos con columnas canónicas excepto las indicadas."""
    header = f"clave_prod_serv,descripcion,cantidad,{valor_unitario_col},{importe_col}"
    row = "84111506,Servicio,1,100.00,100.00"
    return header, row


# ---------------------------------------------------------------------------
# Tests de _ALIAS_MAP (nivel unitario: sólo el dict, sin I/O)
# ---------------------------------------------------------------------------


class TestAliasMapClaveProdServ:
    def test_codigo_con_acento(self) -> None:
        assert _ALIAS_MAP["código"] == "clave_prod_serv"

    def test_codigo_sin_acento(self) -> None:
        assert _ALIAS_MAP["codigo"] == "clave_prod_serv"

    def test_clave_concepto(self) -> None:
        assert _ALIAS_MAP["clave_concepto"] == "clave_prod_serv"

    def test_claveprodserv_camelcase(self) -> None:
        assert _ALIAS_MAP["claveprodserv"] == "clave_prod_serv"

    def test_clave_sat(self) -> None:
        assert _ALIAS_MAP["clave_sat"] == "clave_prod_serv"


class TestAliasMapDescripcion:
    def test_nombre(self) -> None:
        assert _ALIAS_MAP["nombre"] == "descripcion"

    def test_nombre_producto(self) -> None:
        assert _ALIAS_MAP["nombre_producto"] == "descripcion"

    def test_producto(self) -> None:
        assert _ALIAS_MAP["producto"] == "descripcion"


class TestAliasMapCantidad:
    def test_piezas(self) -> None:
        assert _ALIAS_MAP["piezas"] == "cantidad"

    def test_unidades(self) -> None:
        assert _ALIAS_MAP["unidades"] == "cantidad"


class TestAliasMapValorUnitario:
    def test_valorunitario_camelcase(self) -> None:
        assert _ALIAS_MAP["valorunitario"] == "valor_unitario"

    def test_precio_unit(self) -> None:
        assert _ALIAS_MAP["precio_unit"] == "valor_unitario"

    def test_precio_unit_con_espacio(self) -> None:
        assert _ALIAS_MAP["precio unit"] == "valor_unitario"


class TestAliasMapTasa:
    def test_iva(self) -> None:
        assert _ALIAS_MAP["iva"] == "tasa"

    def test_porcentaje_iva_con_espacio(self) -> None:
        assert _ALIAS_MAP["% iva"] == "tasa"

    def test_porcentaje_iva_sin_espacio(self) -> None:
        assert _ALIAS_MAP["%iva"] == "tasa"

    def test_tasaocuota_camelcase(self) -> None:
        assert _ALIAS_MAP["tasaocuota"] == "tasa"


# ---------------------------------------------------------------------------
# Tests de parsear_tabla con CSV temporales (aliases CONTPAQi)
# ---------------------------------------------------------------------------


class TestParseAliasesCONTPAQi:
    def test_codigo_mapea_a_clave_prod_serv(self) -> None:
        """'Código' (mayúscula+acento) → clave_prod_serv."""
        tmp = _csv_tmp(
            "Código,descripcion,cantidad,valor_unitario,importe",
            "84111506,Serv,1,100.00,100.00",
        )
        try:
            result = parsear_tabla(tmp)
        finally:
            tmp.unlink()
        assert "clave_prod_serv" in result.columnas_detectadas
        assert result.registros[0].clave_prod_serv == "84111506"

    def test_nombre_mapea_a_descripcion(self) -> None:
        """'Nombre' → descripcion."""
        tmp = _csv_tmp(
            "clave_prod_serv,Nombre,cantidad,valor_unitario,importe",
            "84111506,Papel A4,10,50.00,500.00",
        )
        try:
            result = parsear_tabla(tmp)
        finally:
            tmp.unlink()
        assert "descripcion" in result.columnas_detectadas
        assert result.registros[0].descripcion == "Papel A4"

    def test_piezas_mapea_a_cantidad(self) -> None:
        """'Piezas' → cantidad."""
        tmp = _csv_tmp(
            "clave_prod_serv,descripcion,Piezas,valor_unitario,importe",
            "84111506,Tóner,3,500.00,1500.00",
        )
        try:
            result = parsear_tabla(tmp)
        finally:
            tmp.unlink()
        assert "cantidad" in result.columnas_detectadas
        assert result.registros[0].cantidad == Decimal("3")

    def test_precio_unit_mapea_a_valor_unitario(self) -> None:
        """'Precio Unit' (con espacio) → valor_unitario."""
        tmp = _csv_tmp(
            "clave_prod_serv,descripcion,cantidad,Precio Unit,importe",
            "84111506,Serv,2,750.00,1500.00",
        )
        try:
            result = parsear_tabla(tmp)
        finally:
            tmp.unlink()
        assert "valor_unitario" in result.columnas_detectadas
        assert result.registros[0].valor_unitario == Decimal("750.00")

    def test_valorunitario_mapea_a_valor_unitario(self) -> None:
        """'ValorUnitario' (camelCase) → valor_unitario."""
        tmp = _csv_tmp(
            "clave_prod_serv,descripcion,cantidad,ValorUnitario,importe",
            "84111506,Serv,1,1200.00,1200.00",
        )
        try:
            result = parsear_tabla(tmp)
        finally:
            tmp.unlink()
        assert "valor_unitario" in result.columnas_detectadas

    def test_porcentaje_iva_mapea_a_tasa(self) -> None:
        """'% IVA' → tasa; el IVA estimado se calcula correctamente."""
        tmp = _csv_tmp(
            "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,% IVA",
            "84111506,Consultoría,1,2500.00,2500.00,0.16",
        )
        try:
            result = parsear_tabla(tmp)
        finally:
            tmp.unlink()
        assert "tasa" in result.columnas_detectadas
        assert result.registros[0].iva_estimado == Decimal("400.00")

    def test_iva_mapea_a_tasa(self) -> None:
        """'IVA' (sencillo) → tasa."""
        tmp = _csv_tmp(
            "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,IVA",
            "84111506,Honorarios,1,5000.00,5000.00,0.16",
        )
        try:
            result = parsear_tabla(tmp)
        finally:
            tmp.unlink()
        assert "tasa" in result.columnas_detectadas
        assert result.registros[0].iva_estimado == Decimal("800.00")

    def test_tasaocuota_mapea_a_tasa(self) -> None:
        """'TasaOCuota' (camelCase CFDI) → tasa."""
        tmp = _csv_tmp(
            "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,TasaOCuota",
            "84111506,Serv,1,3000.00,3000.00,0.16",
        )
        try:
            result = parsear_tabla(tmp)
        finally:
            tmp.unlink()
        assert "tasa" in result.columnas_detectadas

    def test_tasa_exento_genera_advertencia(self) -> None:
        """Valor 'Exento' en columna IVA genera advertencia tasa_no_numerica, no error."""
        tmp = _csv_tmp(
            "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,IVA",
            "01010101,Servicios médicos,1,3200.00,3200.00,Exento",
        )
        try:
            result = parsear_tabla(tmp)
        finally:
            tmp.unlink()
        assert result.registros[0].iva_estimado is None
        adv_tipos = [
            getattr(a, "tipo", None) for a in result.advertencias
        ]
        assert "tasa_no_numerica" in adv_tipos


# ---------------------------------------------------------------------------
# Tests sobre fixtures CONTPAQi reales (integración ligera)
# ---------------------------------------------------------------------------


class TestFixturesContpaqi:
    def test_comercial_movimientos_columnas_detectadas(self) -> None:
        """comercial_movimientos.xlsx: todas las columnas mapean a canónicos."""
        result = parsear_tabla(FIXTURES_CONTPAQI / "comercial_movimientos.xlsx")
        esperadas = {
            "clave_prod_serv", "descripcion", "cantidad", "valor_unitario", "importe", "tasa"
        }
        assert esperadas.issubset(set(result.columnas_detectadas))

    def test_comercial_movimientos_sin_columnas_extra(self) -> None:
        """comercial_movimientos.xlsx: no hay columnas extra sin mapear."""
        result = parsear_tabla(FIXTURES_CONTPAQI / "comercial_movimientos.xlsx")
        for reg in result.registros:
            assert reg.columnas_extra == {}, f"Fila {reg.fila} tiene extras: {reg.columnas_extra}"

    def test_comercial_movimientos_registros(self) -> None:
        """comercial_movimientos.xlsx: 6 filas de datos."""
        result = parsear_tabla(FIXTURES_CONTPAQI / "comercial_movimientos.xlsx")
        assert result.total_registros == 6

    def test_factura_electronica_columnas_detectadas(self) -> None:
        """factura_electronica_conceptos.xlsx: columnas camelCase mapeadas."""
        result = parsear_tabla(FIXTURES_CONTPAQI / "factura_electronica_conceptos.xlsx")
        esperadas = {
            "clave_prod_serv", "descripcion", "cantidad", "valor_unitario", "importe", "tasa"
        }
        assert esperadas.issubset(set(result.columnas_detectadas))

    def test_factura_electronica_iva_calculado(self) -> None:
        """factura_electronica_conceptos.xlsx: total_iva_estimado correcto."""
        result = parsear_tabla(FIXTURES_CONTPAQI / "factura_electronica_conceptos.xlsx")
        assert result.total_iva_estimado == Decimal("5136.00")

    def test_add_hoja_electronica_columnas_detectadas(self) -> None:
        """add_hoja_electronica.xlsx: IVA mapeado a tasa."""
        result = parsear_tabla(FIXTURES_CONTPAQI / "add_hoja_electronica.xlsx")
        assert "tasa" in result.columnas_detectadas

    def test_add_hoja_electronica_exento_genera_advertencia(self) -> None:
        """add_hoja_electronica.xlsx: fila con 'Exento' genera advertencia, no error."""
        result = parsear_tabla(FIXTURES_CONTPAQI / "add_hoja_electronica.xlsx")
        adv_tipos = [getattr(a, "tipo", None) for a in result.advertencias]
        assert "tasa_no_numerica" in adv_tipos

    def test_add_hoja_electronica_tasa_frontera(self) -> None:
        """add_hoja_electronica.xlsx: fila con IVA 0.08 (frontera) → iva_estimado correcto."""
        result = parsear_tabla(FIXTURES_CONTPAQI / "add_hoja_electronica.xlsx")
        # Última fila: importe=4000, tasa=0.08 → iva=320
        ultima = result.registros[-1]
        assert ultima.iva_estimado == Decimal("320.00")

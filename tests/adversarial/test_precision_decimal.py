"""Pruebas adversariales de precisión decimal.

Objetivo: garantizar que ningún importe pierda decimales al pasar por
el pipeline XML → Decimal → JSON string. Ni redondeo, ni notación
científica, ni pérdida de ceros significativos.
"""

import json
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from contiinia.parsers.xml import parsear_xml

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def fx(nombre: str) -> Path:
    return FIXTURES / nombre


# ---------------------------------------------------------------------------
# ADV-DEC-01: cfdi_ingreso.xml — todos los importes son strings, no int/float
# ---------------------------------------------------------------------------


def _collect_all_values(obj: object, path: str = "") -> list[tuple[str, object]]:
    """Recolecta todos los valores primitivos con su ruta JSON."""
    result = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            result.extend(_collect_all_values(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            result.extend(_collect_all_values(v, f"{path}[{i}]"))
    else:
        result.append((path, obj))
    return result


def test_ingreso_total_es_string() -> None:
    """ADV-DEC-01: total en JSON es str, no int ni float."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    assert isinstance(data["total"], str), (
        f"total debe ser str, pero es {type(data['total'])}: {data['total']!r}"
    )


def test_ingreso_subtotal_es_string() -> None:
    """ADV-DEC-01b: subtotal en JSON es str, no int ni float."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    assert isinstance(data["subtotal"], str), (
        f"subtotal debe ser str, pero es {type(data['subtotal'])}: {data['subtotal']!r}"
    )


def test_ingreso_conceptos_importe_es_string() -> None:
    """ADV-DEC-01c: importe en conceptos es str."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    for i, concepto in enumerate(data.get("conceptos", [])):
        assert isinstance(concepto["importe"], str), (
            f"conceptos[{i}].importe debe ser str: {concepto['importe']!r}"
        )


def test_ingreso_conceptos_valor_unitario_es_string() -> None:
    """ADV-DEC-01d: valor_unitario en conceptos es str."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    for i, concepto in enumerate(data.get("conceptos", [])):
        assert isinstance(concepto["valor_unitario"], str), (
            f"conceptos[{i}].valor_unitario debe ser str: {concepto['valor_unitario']!r}"
        )


def test_ingreso_conceptos_cantidad_es_string() -> None:
    """ADV-DEC-01e: cantidad en conceptos es str."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    for i, concepto in enumerate(data.get("conceptos", [])):
        assert isinstance(concepto["cantidad"], str), (
            f"conceptos[{i}].cantidad debe ser str: {concepto['cantidad']!r}"
        )


def test_ingreso_traslados_tasa_o_cuota_es_string() -> None:
    """ADV-DEC-01f: tasa_o_cuota en traslados es str."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    for t in data.get("impuestos", {}).get("traslados", []):
        if "tasa_o_cuota" in t:
            assert isinstance(t["tasa_o_cuota"], str), (
                f"tasa_o_cuota debe ser str: {t['tasa_o_cuota']!r}"
            )


def test_ingreso_traslados_importe_es_string() -> None:
    """ADV-DEC-01g: importe en traslados globales es str."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    for t in data.get("impuestos", {}).get("traslados", []):
        if "importe" in t:
            assert isinstance(t["importe"], str), (
                f"importe de traslado debe ser str: {t['importe']!r}"
            )


def test_ingreso_total_impuestos_trasladados_es_string() -> None:
    """ADV-DEC-01h: total_impuestos_trasladados es str cuando presente."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    if "total_impuestos_trasladados" in data:
        assert isinstance(data["total_impuestos_trasladados"], str), (
            f"total_impuestos_trasladados debe ser str: {data['total_impuestos_trasladados']!r}"
        )


# ---------------------------------------------------------------------------
# ADV-DEC-02: XML sintético con importe "999999999.99" — precisión exacta
# ---------------------------------------------------------------------------


_XML_MONTO_GRANDE = """\
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  Version="4.0" Fecha="2024-03-15T10:00:00" Sello="X" NoCertificado="1"
  Certificado="X" SubTotal="999999999.99" Moneda="MXN" Total="999999999.99"
  TipoDeComprobante="I" Exportacion="01" LugarExpedicion="06600">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="X" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB020202BBB" Nombre="X"
    DomicilioFiscalReceptor="64000" RegimenFiscalReceptor="601"
    UsoCFDI="G01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="81161500" ClaveUnidad="H87"
      Cantidad="1.000" Descripcion="Monto maximo"
      ValorUnitario="999999999.99" Importe="999999999.99" ObjetoImp="02"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
      Version="1.1" UUID="AAAAAAAA-0000-0000-0000-000000000002"
      FechaTimbrado="2024-03-15T10:05:00" RfcProvCertif="SAT970701NN3"
      NoCertificadoSAT="20001000000300022323"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""


def test_monto_grande_parsea_exacto() -> None:
    """ADV-DEC-02: importe '999999999.99' se parsea exactamente como Decimal."""
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", encoding="utf-8", delete=False) as f:
        f.write(_XML_MONTO_GRANDE)
        ruta_tmp = f.name

    try:
        cfdi = parsear_xml(ruta_tmp)
        assert cfdi.total == Decimal("999999999.99"), (
            f"total esperado Decimal('999999999.99'), obtenido {cfdi.total!r}"
        )
        assert cfdi.subtotal == Decimal("999999999.99")
    finally:
        import os
        os.unlink(ruta_tmp)


def test_monto_grande_json_sin_perdida() -> None:
    """ADV-DEC-02b: '999999999.99' en JSON sale como string exacto, sin redondeo."""
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", encoding="utf-8", delete=False) as f:
        f.write(_XML_MONTO_GRANDE)
        ruta_tmp = f.name

    try:
        cfdi = parsear_xml(ruta_tmp)
        data = json.loads(cfdi.model_dump_json())
        assert data["total"] == "999999999.99", (
            f"total en JSON esperado '999999999.99', obtenido {data['total']!r}"
        )
        assert data["subtotal"] == "999999999.99"
    finally:
        import os
        os.unlink(ruta_tmp)


def test_monto_grande_concepto_importe_sin_perdida() -> None:
    """ADV-DEC-02c: el importe del concepto '999999999.99' no pierde decimales."""
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", encoding="utf-8", delete=False) as f:
        f.write(_XML_MONTO_GRANDE)
        ruta_tmp = f.name

    try:
        cfdi = parsear_xml(ruta_tmp)
        data = json.loads(cfdi.model_dump_json())
        assert data["conceptos"][0]["importe"] == "999999999.99", (
            f"concepto.importe esperado '999999999.99', obtenido {data['conceptos'][0]['importe']!r}"
        )
    finally:
        import os
        os.unlink(ruta_tmp)


# ---------------------------------------------------------------------------
# ADV-DEC-03: Decimal("1160.00") == Decimal(resultado["total"]) — sin pérdida
# ---------------------------------------------------------------------------


def test_decimal_roundtrip_total_ingreso() -> None:
    """ADV-DEC-03: Decimal('1160.00') == Decimal(data['total']) sin pérdida de precisión."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    total_desde_json = Decimal(data["total"])
    assert Decimal("1160.00") == total_desde_json, (
        f"Pérdida de precisión: Decimal('1160.00') != Decimal({data['total']!r})"
    )


def test_decimal_roundtrip_subtotal_ingreso() -> None:
    """ADV-DEC-03b: Decimal('1000.00') == Decimal(data['subtotal'])."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    subtotal_desde_json = Decimal(data["subtotal"])
    assert Decimal("1000.00") == subtotal_desde_json


def test_decimal_roundtrip_tasa_iva() -> None:
    """ADV-DEC-03c: Decimal('0.160000') == Decimal(tasa_o_cuota) en traslado."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    tasa = data["impuestos"]["traslados"][0]["tasa_o_cuota"]
    assert Decimal("0.160000") == Decimal(tasa), (
        f"Tasa IVA: Decimal('0.160000') != Decimal({tasa!r})"
    )


def test_decimal_roundtrip_tasa_frontera() -> None:
    """ADV-DEC-03d: Decimal('0.080000') == Decimal(tasa) en fixture frontera."""
    cfdi = parsear_xml(fx("cfdi_iva_frontera.xml"))
    data = json.loads(cfdi.model_dump_json())
    tasa = data["impuestos"]["traslados"][0]["tasa_o_cuota"]
    assert Decimal("0.080000") == Decimal(tasa), (
        f"Tasa frontera: Decimal('0.080000') != Decimal({tasa!r})"
    )


def test_decimal_roundtrip_egreso_total() -> None:
    """ADV-DEC-03e: Decimal('580.00') == Decimal(data['total']) en egreso."""
    cfdi = parsear_xml(fx("cfdi_egreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    assert Decimal("580.00") == Decimal(data["total"])


# ---------------------------------------------------------------------------
# ADV-DEC-04: Valores con muchos decimales — no notación científica
# ---------------------------------------------------------------------------


_XML_DECIMALES_PRECISION = """\
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  Version="4.0" Fecha="2024-03-15T10:00:00" Sello="X" NoCertificado="1"
  Certificado="X" SubTotal="0.000001" Moneda="MXN" Total="0.000001"
  TipoDeComprobante="I" Exportacion="01" LugarExpedicion="06600">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="X" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB020202BBB" Nombre="X"
    DomicilioFiscalReceptor="64000" RegimenFiscalReceptor="601"
    UsoCFDI="G01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="81161500" ClaveUnidad="H87"
      Cantidad="0.000001" Descripcion="Micro importe"
      ValorUnitario="1.000000" Importe="0.000001" ObjetoImp="02"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
      Version="1.1" UUID="AAAAAAAA-0000-0000-0000-000000000003"
      FechaTimbrado="2024-03-15T10:05:00" RfcProvCertif="SAT970701NN3"
      NoCertificadoSAT="20001000000300022323"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""


def test_micro_importe_no_notacion_cientifica() -> None:
    """ADV-DEC-04: '0.000001' no se convierte en '1E-6' ni '1e-6' en JSON."""
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", encoding="utf-8", delete=False) as f:
        f.write(_XML_DECIMALES_PRECISION)
        ruta_tmp = f.name

    try:
        cfdi = parsear_xml(ruta_tmp)
        data = json.loads(cfdi.model_dump_json())
        total_str = data["total"]
        # No debe ser notación científica
        assert "e" not in total_str.lower(), (
            f"total en notación científica: {total_str!r}"
        )
        # El Decimal original debe coincidir
        assert Decimal(total_str) == Decimal("0.000001")
    finally:
        import os
        os.unlink(ruta_tmp)


# ---------------------------------------------------------------------------
# ADV-DEC-05: Integridad de la cadena Decimal → JSON → Decimal
# ---------------------------------------------------------------------------


def test_roundtrip_decimal_no_introduce_error_flotante() -> None:
    """ADV-DEC-05: los valores no pierden precisión al hacer json.loads(json.dumps(..)).

    Si el implementador usa float internamente (bug), 1160.00 podría
    convertirse en 1160.0000000001 o similar.
    """
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    json_str = cfdi.model_dump_json()
    data = json.loads(json_str)

    total_roundtrip = Decimal(data["total"])
    subtotal_roundtrip = Decimal(data["subtotal"])

    # La diferencia debe ser exactamente cero, no un epsilon flotante
    assert total_roundtrip - Decimal("1160.00") == Decimal("0"), (
        f"Diferencia inesperada en total: {total_roundtrip - Decimal('1160.00')}"
    )
    assert subtotal_roundtrip - Decimal("1000.00") == Decimal("0"), (
        f"Diferencia inesperada en subtotal: {subtotal_roundtrip - Decimal('1000.00')}"
    )


# ---------------------------------------------------------------------------
# ADV-DEC-06: Tasa "0.160000" preserva sus 6 decimales
# ---------------------------------------------------------------------------


def test_tasa_iva_preserva_6_decimales_en_string() -> None:
    """ADV-DEC-06: tasa_o_cuota '0.160000' conserva exactamente 6 decimales.

    Un bug común: Decimal('0.160000') → str → '0.16' (pierden ceros finales).
    """
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    tasa = data["impuestos"]["traslados"][0]["tasa_o_cuota"]
    assert tasa == "0.160000", (
        f"tasa_o_cuota esperada '0.160000', obtenida {tasa!r}. "
        f"Posible perdida de ceros significativos."
    )


def test_tasa_frontera_preserva_6_decimales_en_string() -> None:
    """ADV-DEC-06b: tasa_o_cuota '0.080000' conserva exactamente 6 decimales."""
    cfdi = parsear_xml(fx("cfdi_iva_frontera.xml"))
    data = json.loads(cfdi.model_dump_json())
    tasa = data["impuestos"]["traslados"][0]["tasa_o_cuota"]
    assert tasa == "0.080000", (
        f"tasa_o_cuota esperada '0.080000', obtenida {tasa!r}."
    )

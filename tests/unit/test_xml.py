"""Pruebas unitarias para parsers/xml.py — cubre CA-XML-01 a CA-XML-14."""

import json
from pathlib import Path

import pytest

from contiinia.errors import BusinessError, UnsupportedVersionError, XmlMalformadoError
from contiinia.parsers.xml import parsear_xml

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def fx(nombre: str) -> Path:
    return FIXTURES / nombre


# ---------------------------------------------------------------------------
# CA-XML-01: CFDI 4.0 tipo I válido
# ---------------------------------------------------------------------------


def test_ingreso_valido_tipo_I() -> None:
    """CA-XML-01: CFDI tipo I → exit 0, tipo_comprobante='I'."""
    result = parsear_xml(fx("cfdi_ingreso.xml"))
    assert result.tipo_de_comprobante == "I"


def test_ingreso_total_string() -> None:
    """CA-XML-01 / CA-XML-10: total es Decimal, serializado como string '1160.00'."""
    result = parsear_xml(fx("cfdi_ingreso.xml"))
    assert str(result.total) == "1160.00"


def test_ingreso_uuid_mayusculas() -> None:
    """CA-XML-11: UUID normalizado a mayúsculas."""
    result = parsear_xml(fx("cfdi_ingreso.xml"))
    assert result.uuid == result.uuid.upper()
    assert "9001" in result.uuid


def test_ingreso_iva_16() -> None:
    """CA-XML-14: IVA 16% → tasa_o_cuota='0.160000'."""
    result = parsear_xml(fx("cfdi_ingreso.xml"))
    traslados = result.impuestos.traslados if result.impuestos else []
    assert len(traslados) >= 1
    tasas = [str(t.tasa_o_cuota) for t in traslados]
    assert "0.160000" in tasas


def test_ingreso_emisor() -> None:
    """Emisor correctamente parseado."""
    result = parsear_xml(fx("cfdi_ingreso.xml"))
    assert result.emisor.rfc == "AAA010101AAA"
    assert result.emisor.regimen_fiscal == "601"


def test_ingreso_receptor() -> None:
    """Receptor correctamente parseado."""
    result = parsear_xml(fx("cfdi_ingreso.xml"))
    assert result.receptor.rfc == "BBB020202BBB"
    assert result.receptor.uso_cfdi == "G01"


def test_ingreso_conceptos() -> None:
    """Conceptos parseados con traslados."""
    result = parsear_xml(fx("cfdi_ingreso.xml"))
    assert len(result.conceptos) == 1
    c = result.conceptos[0]
    assert c.clave_prod_serv == "81161500"
    assert len(c.impuestos.traslados) == 1
    assert c.impuestos.traslados[0].tipo_factor == "Tasa"


# ---------------------------------------------------------------------------
# CA-XML-02: tipo E
# ---------------------------------------------------------------------------


def test_egreso_tipo_E() -> None:
    """CA-XML-02: CFDI tipo E → tipo_comprobante='E'."""
    result = parsear_xml(fx("cfdi_egreso.xml"))
    assert result.tipo_de_comprobante == "E"


def test_egreso_total() -> None:
    """Egreso: total='580.00'."""
    result = parsear_xml(fx("cfdi_egreso.xml"))
    assert str(result.total) == "580.00"


# ---------------------------------------------------------------------------
# CA-XML-03: tipo P
# ---------------------------------------------------------------------------


def test_pago_tipo_P() -> None:
    """CA-XML-03: CFDI tipo P → tipo_comprobante='P'."""
    result = parsear_xml(fx("cfdi_pago.xml"))
    assert result.tipo_de_comprobante == "P"


# ---------------------------------------------------------------------------
# CA-XML-04: tipo N
# ---------------------------------------------------------------------------


def test_nomina_tipo_N() -> None:
    """CA-XML-04: CFDI tipo N → tipo_comprobante='N'."""
    result = parsear_xml(fx("cfdi_nomina.xml"))
    assert result.tipo_de_comprobante == "N"


# ---------------------------------------------------------------------------
# CA-XML-05: tipo T
# ---------------------------------------------------------------------------


def test_traslado_tipo_T() -> None:
    """CA-XML-05: CFDI tipo T → tipo_comprobante='T'."""
    result = parsear_xml(fx("cfdi_traslado.xml"))
    assert result.tipo_de_comprobante == "T"


# ---------------------------------------------------------------------------
# CA-XML-06: CFDI 3.3 → UnsupportedVersionError
# ---------------------------------------------------------------------------


def test_cfdi_33_lanza_unsupported() -> None:
    """CA-XML-06: CFDI 3.3 → UnsupportedVersionError."""
    with pytest.raises(UnsupportedVersionError):
        parsear_xml(fx("cfdi_3.3_rechazado.xml"))


# ---------------------------------------------------------------------------
# CA-XML-07: XML malformado → XmlMalformadoError (SystemError exit 3)
# ---------------------------------------------------------------------------


def test_xml_corrupto_lanza_system_error() -> None:
    """CA-XML-07: XML malformado → XmlMalformadoError."""
    with pytest.raises(XmlMalformadoError):
        parsear_xml(fx("cfdi_xml_corrupto.xml"))


# ---------------------------------------------------------------------------
# CA-XML-10: Ningún importe es float; todos son string en JSON
# ---------------------------------------------------------------------------


def test_decimales_serializados_como_string() -> None:
    """CA-XML-10: todos los importes en JSON de salida son string, no number."""
    result = parsear_xml(fx("cfdi_ingreso.xml"))
    json_str = result.model_dump_json(exclude_none=True)
    data = json.loads(json_str)

    def check_no_float(obj: object, path: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                check_no_float(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                check_no_float(v, f"{path}[{i}]")
        elif isinstance(obj, float):
            raise AssertionError(f"Se encontró float en {path}: {obj!r}")

    check_no_float(data)


# ---------------------------------------------------------------------------
# CA-XML-11: UUID normalizado a mayúsculas
# ---------------------------------------------------------------------------


def test_uuid_mayusculas() -> None:
    """CA-XML-11: UUID normalizado a mayúsculas."""
    result = parsear_xml(fx("cfdi_ingreso.xml"))
    assert result.uuid == result.uuid.upper()


# ---------------------------------------------------------------------------
# CA-XML-14: IVA 8% zona frontera
# ---------------------------------------------------------------------------


def test_iva_frontera_tasa_8() -> None:
    """CA-XML-14: IVA 8% → tasa_o_cuota='0.080000'."""
    result = parsear_xml(fx("cfdi_iva_frontera.xml"))
    traslados = result.impuestos.traslados if result.impuestos else []
    tasas = [str(t.tasa_o_cuota) for t in traslados]
    assert "0.080000" in tasas


# ---------------------------------------------------------------------------
# IVA exento
# ---------------------------------------------------------------------------


def test_iva_exento_tipo_factor() -> None:
    """CFDI con TipoFactor=Exento → parseado sin error."""
    result = parsear_xml(fx("cfdi_iva_exento.xml"))
    traslados = result.impuestos.traslados if result.impuestos else []
    assert len(traslados) >= 1
    factores = [t.tipo_factor for t in traslados]
    assert "Exento" in factores


def test_iva_exento_tasa_none() -> None:
    """CFDI exento: TasaOCuota es None (no presente en XML)."""
    result = parsear_xml(fx("cfdi_iva_exento.xml"))
    traslados = result.impuestos.traslados if result.impuestos else []
    exentos = [t for t in traslados if t.tipo_factor == "Exento"]
    assert len(exentos) >= 1
    assert exentos[0].tasa_o_cuota is None


# ---------------------------------------------------------------------------
# Timbre presente
# ---------------------------------------------------------------------------


def test_ingreso_tiene_timbre() -> None:
    """CFDI ingreso: ComplementoTimbre presente."""
    result = parsear_xml(fx("cfdi_ingreso.xml"))
    assert result.complemento_timbre is not None
    assert result.complemento_timbre.rfc_prov_certif == "SAT970701NN3"

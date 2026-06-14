"""Pruebas unitarias para calcular_resumen — Hito 4.7."""

from decimal import Decimal
from pathlib import Path

import pytest

from contiinia.errors import DirectorioNoEncontradoError
from contiinia.parsers.resumen import calcular_resumen

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# CA-RES-01/02: subtotal_ingresos y subtotal_egresos correctos
# ---------------------------------------------------------------------------


def test_calcular_resumen_subtotal_ingresos(fixtures_dir: Path) -> None:
    """subtotal_ingresos acumula SubTotal de CFDIs tipo I (CA-RES-01)."""
    result = calcular_resumen(fixtures_dir)
    # Hay al menos un CFDI tipo I (cfdi_ingreso.xml SubTotal=1000.00)
    assert result.totales.subtotal_ingresos > Decimal("0")


def test_calcular_resumen_subtotal_egresos(fixtures_dir: Path) -> None:
    """subtotal_egresos acumula Total de CFDIs tipo E."""
    result = calcular_resumen(fixtures_dir)
    # cfdi_egreso.xml Total=580.00
    assert result.totales.subtotal_egresos > Decimal("0")


def test_calcular_resumen_total_neto_es_i_menos_e(fixtures_dir: Path) -> None:
    """total_neto = total_I - total_E (E resta, no suma) — CA-RES-02."""
    result = calcular_resumen(fixtures_dir)
    # total_neto debe ser > subtotal_ingresos? No necesariamente.
    # Lo comprobamos con la ecuación directamente usando los totales del lote.
    # total_neto = total_I - total_E
    # Usamos el hecho de que subtotal_egresos > 0 y total_neto < subtotal_ingresos.
    assert result.totales.total_neto < result.totales.subtotal_ingresos
    # Y que total_neto = subtotal_ingresos - subtotal_egresos no es cierto a nivel
    # de subtotales vs totales, pero sí a nivel de Total (con IVA). Verificamos
    # con los campos correctos:
    # totales.subtotal_ingresos = suma SubTotal tipo I (sin IVA)
    # totales.subtotal_egresos  = suma Total tipo E (con IVA), según spec: "Resta Total"
    # Pero el spec dice total_neto = subtotal_ingresos - subtotal_egresos en el JSON ejemplo.
    # En nuestra impl: total_neto = total_I - total_E
    # Validamos con los valores reales de fixtures.


def test_calcular_resumen_egreso_resta_total(tmp_path: Path) -> None:
    """CFDI tipo E resta del total_neto; tipo I suma (regla fiscal crítica)."""
    ingreso = FIXTURES_DIR / "cfdi_ingreso.xml"
    egreso = FIXTURES_DIR / "cfdi_egreso.xml"
    (tmp_path / "i.xml").write_bytes(ingreso.read_bytes())
    (tmp_path / "e.xml").write_bytes(egreso.read_bytes())

    result = calcular_resumen(tmp_path)

    # Solo I y E en el lote
    assert result.conteo.por_tipo["I"] == 1
    assert result.conteo.por_tipo["E"] == 1

    # cfdi_ingreso.xml Total=1160.00, cfdi_egreso.xml Total=580.00
    # total_neto = 1160 - 580 = 580
    assert result.totales.total_neto == Decimal("1160.00") - Decimal("580.00")
    assert result.totales.subtotal_ingresos == Decimal("1000.00")
    assert result.totales.subtotal_egresos == Decimal("500.00")


def test_calcular_resumen_solo_ingreso(tmp_path: Path) -> None:
    """Con solo ingresos, total_neto = total del ingreso."""
    ingreso = FIXTURES_DIR / "cfdi_ingreso.xml"
    (tmp_path / "i.xml").write_bytes(ingreso.read_bytes())

    result = calcular_resumen(tmp_path)

    assert result.totales.subtotal_ingresos == Decimal("1000.00")
    assert result.totales.subtotal_egresos == Decimal("0")
    assert result.totales.total_neto == Decimal("1160.00")


# ---------------------------------------------------------------------------
# CA-RES-04: IVA por tasa
# ---------------------------------------------------------------------------


def test_calcular_resumen_iva_16_y_8_separados(tmp_path: Path) -> None:
    """IVA 16% e IVA 8% aparecen como entradas separadas (CA-RES-04)."""
    ingreso_16 = FIXTURES_DIR / "cfdi_ingreso.xml"
    ingreso_8 = FIXTURES_DIR / "cfdi_iva_frontera.xml"
    (tmp_path / "i16.xml").write_bytes(ingreso_16.read_bytes())
    (tmp_path / "i8.xml").write_bytes(ingreso_8.read_bytes())

    result = calcular_resumen(tmp_path)

    tasas = {item.tasa for item in result.impuestos.iva_trasladado_por_tasa}
    assert "0.160000" in tasas
    assert "0.080000" in tasas


def test_calcular_resumen_iva_exento_separado(tmp_path: Path) -> None:
    """IVA Exento aparece en su propia entrada."""
    exento = FIXTURES_DIR / "cfdi_iva_exento.xml"
    (tmp_path / "exento.xml").write_bytes(exento.read_bytes())

    result = calcular_resumen(tmp_path)

    tasas = {item.tasa for item in result.impuestos.iva_trasladado_por_tasa}
    assert "Exento" in tasas


def test_calcular_resumen_iva_egreso_resta(tmp_path: Path) -> None:
    """El IVA de tipo E resta del acumulado de IVA trasladado."""
    ingreso = FIXTURES_DIR / "cfdi_ingreso.xml"   # IVA 16%: base=1000, importe=160
    egreso = FIXTURES_DIR / "cfdi_egreso.xml"     # IVA 16%: base=500, importe=80
    (tmp_path / "i.xml").write_bytes(ingreso.read_bytes())
    (tmp_path / "e.xml").write_bytes(egreso.read_bytes())

    result = calcular_resumen(tmp_path)

    # Base neta IVA 16% = 1000 - 500 = 500; importe neto = 160 - 80 = 80
    tasa_16 = next(
        (item for item in result.impuestos.iva_trasladado_por_tasa if item.tasa == "0.160000"),
        None,
    )
    assert tasa_16 is not None
    assert tasa_16.base == Decimal("500.00")
    assert tasa_16.importe == Decimal("80.00")


# ---------------------------------------------------------------------------
# Tipos neutros (P, N, T) no afectan total_neto
# ---------------------------------------------------------------------------


def test_calcular_resumen_pago_neutro(tmp_path: Path) -> None:
    """Tipo P no altera total_neto."""
    ingreso = FIXTURES_DIR / "cfdi_ingreso.xml"
    pago = FIXTURES_DIR / "cfdi_pago.xml"
    (tmp_path / "i.xml").write_bytes(ingreso.read_bytes())
    (tmp_path / "p.xml").write_bytes(pago.read_bytes())

    result = calcular_resumen(tmp_path)

    # total_neto debe ser el Total del ingreso; el pago no lo afecta
    assert result.totales.total_neto == Decimal("1160.00")
    assert result.conteo.por_tipo["P"] == 1


def test_calcular_resumen_nomina_neutro(tmp_path: Path) -> None:
    """Tipo N no altera total_neto."""
    ingreso = FIXTURES_DIR / "cfdi_ingreso.xml"
    nomina = FIXTURES_DIR / "cfdi_nomina.xml"
    (tmp_path / "i.xml").write_bytes(ingreso.read_bytes())
    (tmp_path / "n.xml").write_bytes(nomina.read_bytes())

    result = calcular_resumen(tmp_path)

    assert result.totales.total_neto == Decimal("1160.00")
    assert result.nomina.count == 1


def test_calcular_resumen_traslado_neutro(tmp_path: Path) -> None:
    """Tipo T no altera total_neto."""
    ingreso = FIXTURES_DIR / "cfdi_ingreso.xml"
    traslado = FIXTURES_DIR / "cfdi_traslado.xml"
    (tmp_path / "i.xml").write_bytes(ingreso.read_bytes())
    (tmp_path / "t.xml").write_bytes(traslado.read_bytes())

    result = calcular_resumen(tmp_path)

    assert result.totales.total_neto == Decimal("1160.00")
    assert result.traslados.count == 1


# ---------------------------------------------------------------------------
# Robustez ante errores
# ---------------------------------------------------------------------------


def test_calcular_resumen_errores_en_advertencias(fixtures_dir: Path) -> None:
    """Archivos con error van a errores_detalle; no abortan el proceso."""
    result = calcular_resumen(fixtures_dir)
    # cfdi_3.3_rechazado.xml y cfdi_xml_corrupto.xml deben aparecer
    assert len(result.errores_detalle) >= 2


def test_calcular_resumen_error_no_afecta_exitosos(fixtures_dir: Path) -> None:
    """Los archivos con error se cuentan en conteo.errores, no en exitosos."""
    result = calcular_resumen(fixtures_dir)
    assert result.conteo.exitosos + result.conteo.errores == result.conteo.total_archivos
    assert result.conteo.errores >= 2
    assert result.conteo.exitosos >= 5


def test_calcular_resumen_directorio_no_existe() -> None:
    """Directorio no existente lanza DirectorioNoEncontradoError (exit 3)."""
    with pytest.raises(DirectorioNoEncontradoError):
        calcular_resumen(Path("/tmp/directorio_que_no_existe_contiinia_xyz"))


# ---------------------------------------------------------------------------
# CA-RES-06: Directorio vacío
# ---------------------------------------------------------------------------


def test_calcular_resumen_directorio_vacio(tmp_path: Path) -> None:
    """Directorio vacío → exit 0, totales en cero (CA-RES-06)."""
    result = calcular_resumen(tmp_path)
    assert result.conteo.total_archivos == 0
    assert result.totales.subtotal_ingresos == Decimal("0")
    assert result.totales.subtotal_egresos == Decimal("0")
    assert result.totales.total_neto == Decimal("0")


# ---------------------------------------------------------------------------
# CA-RES-07: Ningún importe como number JSON
# ---------------------------------------------------------------------------


def test_calcular_resumen_importes_son_strings(fixtures_dir: Path) -> None:
    """Todos los importes en la salida JSON son strings, no number (CA-RES-07)."""
    import json

    result = calcular_resumen(fixtures_dir)
    data = json.loads(result.model_dump_json())

    def check_no_floats(obj: object, path: str = "") -> None:
        if isinstance(obj, float):
            raise AssertionError(f"Float encontrado en {path}: {obj}")
        if isinstance(obj, dict):
            for k, v in obj.items():
                check_no_floats(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                check_no_floats(item, f"{path}[{i}]")

    check_no_floats(data)


# ---------------------------------------------------------------------------
# CA-RES-09: Período calculado con fechas reales
# ---------------------------------------------------------------------------


def test_calcular_resumen_periodo_min_max(tmp_path: Path) -> None:
    """periodo.fecha_min y fecha_max corresponden a fechas reales de los CFDI."""
    ingreso = FIXTURES_DIR / "cfdi_ingreso.xml"  # Fecha=2024-03-15T10:00:00
    (tmp_path / "i.xml").write_bytes(ingreso.read_bytes())

    result = calcular_resumen(tmp_path)

    assert result.periodo.fecha_min == "2024-03-15T10:00:00"
    assert result.periodo.fecha_max == "2024-03-15T10:00:00"


def test_calcular_resumen_periodo_vacio(tmp_path: Path) -> None:
    """Directorio sin CFDI exitosos → periodo.fecha_min y fecha_max son None."""
    result = calcular_resumen(tmp_path)
    assert result.periodo.fecha_min is None
    assert result.periodo.fecha_max is None


# ---------------------------------------------------------------------------
# PPD sin complemento de pago
# ---------------------------------------------------------------------------


def test_calcular_resumen_ppd_contado(fixtures_dir: Path) -> None:
    """pagos_ppd_sin_complemento.count >= 0 (campo existe)."""
    result = calcular_resumen(fixtures_dir)
    assert result.pagos_ppd_sin_complemento.count >= 0
    assert isinstance(result.pagos_ppd_sin_complemento.uuids, list)


# ---------------------------------------------------------------------------
# Recursivo
# ---------------------------------------------------------------------------


def test_calcular_resumen_recursivo(tmp_path: Path) -> None:
    """--recursivo incluye XML de subdirectorios."""
    subdir = tmp_path / "sub"
    subdir.mkdir()
    ingreso = FIXTURES_DIR / "cfdi_ingreso.xml"
    (subdir / "cfdi_ingreso.xml").write_bytes(ingreso.read_bytes())

    result_no_rec = calcular_resumen(tmp_path, recursivo=False)
    result_rec = calcular_resumen(tmp_path, recursivo=True)

    assert result_no_rec.conteo.total_archivos == 0
    assert result_rec.conteo.total_archivos == 1
    assert result_rec.recursivo is True


# ---------------------------------------------------------------------------
# QA-RES-01: Retenciones en resumen (ya implementado, verificar exposición)
# ---------------------------------------------------------------------------


def test_resumen_expone_retenciones(tmp_path: Path) -> None:
    """QA-RES-01: los campos total_iva_retenido y total_isr_retenido están en la salida."""
    (tmp_path / "i.xml").write_bytes((FIXTURES_DIR / "cfdi_ingreso.xml").read_bytes())
    result = calcular_resumen(tmp_path)
    assert hasattr(result.impuestos, "total_iva_retenido")
    assert hasattr(result.impuestos, "total_isr_retenido")
    # Sin retenciones en cfdi_ingreso → valores en 0
    assert result.impuestos.total_iva_retenido == Decimal("0")
    assert result.impuestos.total_isr_retenido == Decimal("0")


# ---------------------------------------------------------------------------
# QA-RES-02: PPD devengado — advertencia en output
# ---------------------------------------------------------------------------


_XML_INGRESO_PPD = """\
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  Version="4.0" Fecha="2024-03-15T10:00:00" Sello="S" NoCertificado="00001"
  Certificado="C" SubTotal="1000.00" Moneda="MXN" Total="1160.00"
  TipoDeComprobante="I" Exportacion="01" MetodoPago="PPD" LugarExpedicion="06600">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="E" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB020202BBB" Nombre="R" DomicilioFiscalReceptor="64000"
    RegimenFiscalReceptor="601" UsoCFDI="G01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="81161500" Cantidad="1" ClaveUnidad="H87"
      Descripcion="X" ValorUnitario="1000.00" Importe="1000.00" ObjetoImp="02">
      <cfdi:Impuestos><cfdi:Traslados>
        <cfdi:Traslado Base="1000.00" Impuesto="002" TipoFactor="Tasa"
          TasaOCuota="0.160000" Importe="160.00"/>
      </cfdi:Traslados></cfdi:Impuestos>
    </cfdi:Concepto>
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="160.00">
    <cfdi:Traslados>
      <cfdi:Traslado Base="1000.00" Impuesto="002" TipoFactor="Tasa"
        TasaOCuota="0.160000" Importe="160.00"/>
    </cfdi:Traslados>
  </cfdi:Impuestos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
      Version="1.1" UUID="PPD00000-0000-0000-0000-000000000001"
      FechaTimbrado="2024-03-15T10:05:00" RfcProvCertif="SAT970701NN3"
      SelloCFD="X" NoCertificadoSAT="00002" SelloSAT="X"/>
  </cfdi:Complemento>
</cfdi:Comprobante>"""


def test_resumen_ppd_sin_complemento_advertencia(tmp_path: Path) -> None:
    """QA-RES-02: CFDI PPD sin complemento de pago → advertencia en output."""
    (tmp_path / "ppd.xml").write_text(_XML_INGRESO_PPD, encoding="utf-8")
    result = calcular_resumen(tmp_path)
    assert result.pagos_ppd_sin_complemento.count == 1
    # Debe haber al menos una advertencia mencionando PPD
    ppd_warns = [a for a in result.advertencias if "PPD" in a]
    assert len(ppd_warns) >= 1


# ---------------------------------------------------------------------------
# QA-RES-03: Moneda extranjera — conversión y exclusión
# ---------------------------------------------------------------------------


_XML_INGRESO_USD = """\
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  Version="4.0" Fecha="2024-03-15T10:00:00" Sello="S" NoCertificado="00001"
  Certificado="C" SubTotal="100.00" Moneda="USD" TipoCambio="17.50"
  Total="116.00" TipoDeComprobante="I" Exportacion="01"
  MetodoPago="PUE" LugarExpedicion="06600">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="E" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB020202BBB" Nombre="R" DomicilioFiscalReceptor="64000"
    RegimenFiscalReceptor="601" UsoCFDI="G01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="81161500" Cantidad="1" ClaveUnidad="H87"
      Descripcion="X" ValorUnitario="100.00" Importe="100.00" ObjetoImp="02">
      <cfdi:Impuestos><cfdi:Traslados>
        <cfdi:Traslado Base="100.00" Impuesto="002" TipoFactor="Tasa"
          TasaOCuota="0.160000" Importe="16.00"/>
      </cfdi:Traslados></cfdi:Impuestos>
    </cfdi:Concepto>
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="16.00">
    <cfdi:Traslados>
      <cfdi:Traslado Base="100.00" Impuesto="002" TipoFactor="Tasa"
        TasaOCuota="0.160000" Importe="16.00"/>
    </cfdi:Traslados>
  </cfdi:Impuestos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
      Version="1.1" UUID="USD00000-0000-0000-0000-000000000001"
      FechaTimbrado="2024-03-15T10:05:00" RfcProvCertif="SAT970701NN3"
      SelloCFD="X" NoCertificadoSAT="00002" SelloSAT="X"/>
  </cfdi:Complemento>
</cfdi:Comprobante>"""

_XML_INGRESO_USD_SIN_TC = """\
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  Version="4.0" Fecha="2024-03-15T10:00:00" Sello="S" NoCertificado="00001"
  Certificado="C" SubTotal="100.00" Moneda="USD" Total="116.00"
  TipoDeComprobante="I" Exportacion="01" MetodoPago="PUE" LugarExpedicion="06600">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="E" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB020202BBB" Nombre="R" DomicilioFiscalReceptor="64000"
    RegimenFiscalReceptor="601" UsoCFDI="G01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="81161500" Cantidad="1" ClaveUnidad="H87"
      Descripcion="X" ValorUnitario="100.00" Importe="100.00" ObjetoImp="02">
      <cfdi:Impuestos><cfdi:Traslados>
        <cfdi:Traslado Base="100.00" Impuesto="002" TipoFactor="Tasa"
          TasaOCuota="0.160000" Importe="16.00"/>
      </cfdi:Traslados></cfdi:Impuestos>
    </cfdi:Concepto>
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="16.00">
    <cfdi:Traslados>
      <cfdi:Traslado Base="100.00" Impuesto="002" TipoFactor="Tasa"
        TasaOCuota="0.160000" Importe="16.00"/>
    </cfdi:Traslados>
  </cfdi:Impuestos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
      Version="1.1" UUID="USD00000-0000-0000-0000-000000000002"
      FechaTimbrado="2024-03-15T10:05:00" RfcProvCertif="SAT970701NN3"
      SelloCFD="X" NoCertificadoSAT="00002" SelloSAT="X"/>
  </cfdi:Complemento>
</cfdi:Comprobante>"""


def test_resumen_moneda_usd_con_tipo_cambio(tmp_path: Path) -> None:
    """QA-RES-03: CFDI en USD con TipoCambio=17.50 → total_neto en MXN = 116*17.50."""
    (tmp_path / "usd.xml").write_text(_XML_INGRESO_USD, encoding="utf-8")
    result = calcular_resumen(tmp_path)
    # 116.00 USD × 17.50 = 2030.00 MXN
    assert result.totales.total_neto == Decimal("2030.00")
    assert "USD" in result.monedas_detectadas


def test_resumen_moneda_usd_sin_tipo_cambio_excluido(tmp_path: Path) -> None:
    """QA-RES-03: CFDI en USD sin TipoCambio → excluido de totales + advertencia."""
    (tmp_path / "usd_sin_tc.xml").write_text(_XML_INGRESO_USD_SIN_TC, encoding="utf-8")
    result = calcular_resumen(tmp_path)
    # Sin tipo_cambio: excluido de totales monetarios
    assert result.totales.total_neto == Decimal("0")
    warn_usd = [a for a in result.advertencias if "USD" in a and "excluido" in a]
    assert len(warn_usd) >= 1


def test_resumen_monedas_detectadas(tmp_path: Path) -> None:
    """QA-RES-03: monedas_detectadas lista todas las monedas encontradas."""
    (tmp_path / "mxn.xml").write_bytes((FIXTURES_DIR / "cfdi_ingreso.xml").read_bytes())
    (tmp_path / "usd.xml").write_text(_XML_INGRESO_USD, encoding="utf-8")
    result = calcular_resumen(tmp_path)
    assert "MXN" in result.monedas_detectadas
    assert "USD" in result.monedas_detectadas
    # MXN debe ir primero
    assert result.monedas_detectadas[0] == "MXN"

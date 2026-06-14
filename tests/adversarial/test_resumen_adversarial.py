"""Pruebas adversariales para el parser/agregador de resumen.

Objetivo: verificar que la lógica de resta de egresos, la neutralidad
de tipos P/N/T y el comportamiento en directorios edge case son correctos.
"""

import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from contiinia.parsers.resumen import calcular_resumen

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# ADV-RES-01: subtotal_neto = subtotal_ingreso - subtotal_egreso
# Usando los fixtures reales del directorio fixtures/
# I: subtotal=1000.00, E: subtotal=500.00 → subtotal_ingresos=1000, subtotal_egresos=500
# Pero como hay más archivos en fixtures/ (pago, nomina, traslado, frontera, exento, dup)
# usamos un directorio temporal con solo I y E para control exacto.
# ---------------------------------------------------------------------------


def _crear_xml_ingreso(directorio: Path, nombre: str = "ingreso.xml") -> Path:
    """Crea un CFDI tipo I mínimo en directorio."""
    contenido = """\
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  Version="4.0" Fecha="2024-03-15T10:00:00" Sello="X" NoCertificado="1"
  Certificado="X" SubTotal="1000.00" Moneda="MXN" Total="1160.00"
  TipoDeComprobante="I" Exportacion="01" LugarExpedicion="06600">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="X" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB020202BBB" Nombre="X"
    DomicilioFiscalReceptor="64000" RegimenFiscalReceptor="601"
    UsoCFDI="G01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="81161500" ClaveUnidad="H87"
      Cantidad="1" Descripcion="Test" ValorUnitario="1000.00"
      Importe="1000.00" ObjetoImp="02"/>
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="160.00">
    <cfdi:Traslados>
      <cfdi:Traslado Base="1000.00" Impuesto="002" TipoFactor="Tasa"
        TasaOCuota="0.160000" Importe="160.00"/>
    </cfdi:Traslados>
  </cfdi:Impuestos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
      Version="1.1" UUID="AAAA0000-0000-0000-0000-000000000001"
      FechaTimbrado="2024-03-15T10:05:00" RfcProvCertif="SAT970701NN3"
      SelloCFD="X" NoCertificadoSAT="2" SelloSAT="X"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""
    ruta = directorio / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def _crear_xml_egreso(directorio: Path, nombre: str = "egreso.xml") -> Path:
    """Crea un CFDI tipo E mínimo en directorio."""
    contenido = """\
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  Version="4.0" Fecha="2024-03-16T10:00:00" Sello="X" NoCertificado="1"
  Certificado="X" SubTotal="400.00" Moneda="MXN" Total="464.00"
  TipoDeComprobante="E" Exportacion="01" LugarExpedicion="06600">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="X" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB020202BBB" Nombre="X"
    DomicilioFiscalReceptor="64000" RegimenFiscalReceptor="601"
    UsoCFDI="G01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="81161500" ClaveUnidad="H87"
      Cantidad="1" Descripcion="NC" ValorUnitario="400.00"
      Importe="400.00" ObjetoImp="02"/>
  </cfdi:Conceptos>
  <cfdi:Impuestos TotalImpuestosTrasladados="64.00">
    <cfdi:Traslados>
      <cfdi:Traslado Base="400.00" Impuesto="002" TipoFactor="Tasa"
        TasaOCuota="0.160000" Importe="64.00"/>
    </cfdi:Traslados>
  </cfdi:Impuestos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
      Version="1.1" UUID="BBBB0000-0000-0000-0000-000000000002"
      FechaTimbrado="2024-03-16T10:05:00" RfcProvCertif="SAT970701NN3"
      SelloCFD="X" NoCertificadoSAT="2" SelloSAT="X"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""
    ruta = directorio / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def _crear_xml_pago(directorio: Path, nombre: str = "pago.xml") -> Path:
    """Crea un CFDI tipo P (neutro) en directorio."""
    contenido = """\
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  Version="4.0" Fecha="2024-03-17T10:00:00" Sello="X" NoCertificado="1"
  Certificado="X" SubTotal="0" Moneda="XXX" Total="0"
  TipoDeComprobante="P" Exportacion="01" LugarExpedicion="06600">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="X" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB020202BBB" Nombre="X"
    DomicilioFiscalReceptor="64000" RegimenFiscalReceptor="601"
    UsoCFDI="CP01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="84111506" ClaveUnidad="ACT"
      Cantidad="1" Descripcion="Pago" ValorUnitario="0"
      Importe="0" ObjetoImp="01"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
      Version="1.1" UUID="CCCC0000-0000-0000-0000-000000000003"
      FechaTimbrado="2024-03-17T10:05:00" RfcProvCertif="SAT970701NN3"
      SelloCFD="X" NoCertificadoSAT="2" SelloSAT="X"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""
    ruta = directorio / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def _crear_xml_nomina(directorio: Path, nombre: str = "nomina.xml") -> Path:
    """Crea un CFDI tipo N (neutro) en directorio."""
    contenido = """\
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  Version="4.0" Fecha="2024-03-31T10:00:00" Sello="X" NoCertificado="1"
  Certificado="X" SubTotal="9999.99" Moneda="MXN" Total="9999.99"
  TipoDeComprobante="N" Exportacion="01" LugarExpedicion="06600">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="X" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="CURP001" Nombre="Empleado"
    DomicilioFiscalReceptor="06600" RegimenFiscalReceptor="605"
    UsoCFDI="CN01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="84111505" ClaveUnidad="ACT"
      Cantidad="1" Descripcion="Nomina"
      ValorUnitario="9999.99" Importe="9999.99" ObjetoImp="01"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
      Version="1.1" UUID="DDDD0000-0000-0000-0000-000000000004"
      FechaTimbrado="2024-03-31T10:05:00" RfcProvCertif="SAT970701NN3"
      SelloCFD="X" NoCertificadoSAT="2" SelloSAT="X"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""
    ruta = directorio / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def _crear_xml_traslado(directorio: Path, nombre: str = "traslado.xml") -> Path:
    """Crea un CFDI tipo T (neutro) en directorio."""
    contenido = """\
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  Version="4.0" Fecha="2024-03-18T10:00:00" Sello="X" NoCertificado="1"
  Certificado="X" SubTotal="0" Moneda="XXX" Total="0"
  TipoDeComprobante="T" Exportacion="01" LugarExpedicion="06600">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="X" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="AAA010101AAA" Nombre="X"
    DomicilioFiscalReceptor="06600" RegimenFiscalReceptor="601"
    UsoCFDI="S01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="78101801" ClaveUnidad="KGM"
      Cantidad="10" Descripcion="Traslado"
      ValorUnitario="0" Importe="0" ObjetoImp="01"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
      Version="1.1" UUID="EEEE0000-0000-0000-0000-000000000005"
      FechaTimbrado="2024-03-18T10:05:00" RfcProvCertif="SAT970701NN3"
      SelloCFD="X" NoCertificadoSAT="2" SelloSAT="X"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""
    ruta = directorio / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


# ---------------------------------------------------------------------------
# ADV-RES-01: subtotal_neto = subtotal_ingreso - subtotal_egreso
# ---------------------------------------------------------------------------


def test_resumen_egreso_resta_del_subtotal() -> None:
    """ADV-RES-01: tipo E resta de subtotal_ingresos en el total neto."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        _crear_xml_ingreso(d)
        _crear_xml_egreso(d)
        resumen = calcular_resumen(d)

        # subtotal_ingresos = 1000.00 (del tipo I)
        assert resumen.totales.subtotal_ingresos == Decimal("1000.00"), (
            f"subtotal_ingresos esperado 1000.00, obtenido {resumen.totales.subtotal_ingresos}"
        )
        # subtotal_egresos = 400.00 (del tipo E)
        assert resumen.totales.subtotal_egresos == Decimal("400.00"), (
            f"subtotal_egresos esperado 400.00, obtenido {resumen.totales.subtotal_egresos}"
        )
        # total_neto = total_I - total_E = 1160.00 - 464.00 = 696.00
        assert resumen.totales.total_neto == Decimal("696.00"), (
            f"total_neto esperado 696.00, obtenido {resumen.totales.total_neto}"
        )


def test_resumen_egreso_resta_iva_trasladado() -> None:
    """ADV-RES-01b: tipo E también resta el IVA del totales de traslados."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        _crear_xml_ingreso(d)   # IVA: 160.00
        _crear_xml_egreso(d)    # IVA: 64.00 (se resta)
        resumen = calcular_resumen(d)
        # IVA neto = 160.00 - 64.00 = 96.00
        assert resumen.impuestos.total_iva_trasladado == Decimal("96.00"), (
            f"IVA trasladado neto esperado 96.00, obtenido {resumen.impuestos.total_iva_trasladado}"
        )


def test_resumen_sin_egreso_total_neto_igual_total_ingreso() -> None:
    """ADV-RES-01c: sin egresos, total_neto == total del ingreso."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        _crear_xml_ingreso(d)
        resumen = calcular_resumen(d)
        assert resumen.totales.total_neto == Decimal("1160.00")
        assert resumen.totales.subtotal_egresos == Decimal("0")


# ---------------------------------------------------------------------------
# ADV-RES-02: tipos P, N, T NO afectan el total_neto del resumen
# ---------------------------------------------------------------------------


def test_resumen_tipo_P_no_afecta_total_neto() -> None:
    """ADV-RES-02: agregar tipo P no cambia total_neto."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        _crear_xml_ingreso(d)
        resumen_sin_p = calcular_resumen(d)
        total_sin_p = resumen_sin_p.totales.total_neto

        _crear_xml_pago(d)
        resumen_con_p = calcular_resumen(d)
        total_con_p = resumen_con_p.totales.total_neto

        assert total_sin_p == total_con_p, (
            f"Tipo P afecto total_neto: sin_P={total_sin_p}, con_P={total_con_p}"
        )


def test_resumen_tipo_N_no_afecta_total_neto() -> None:
    """ADV-RES-02b: agregar tipo N (nómina) no cambia total_neto."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        _crear_xml_ingreso(d)
        resumen_sin_n = calcular_resumen(d)
        total_sin_n = resumen_sin_n.totales.total_neto

        _crear_xml_nomina(d)
        resumen_con_n = calcular_resumen(d)
        total_con_n = resumen_con_n.totales.total_neto

        assert total_sin_n == total_con_n, (
            f"Tipo N afecto total_neto: sin_N={total_sin_n}, con_N={total_con_n}"
        )


def test_resumen_tipo_T_no_afecta_total_neto() -> None:
    """ADV-RES-02c: agregar tipo T (traslado) no cambia total_neto."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        _crear_xml_ingreso(d)
        resumen_sin_t = calcular_resumen(d)
        total_sin_t = resumen_sin_t.totales.total_neto

        _crear_xml_traslado(d)
        resumen_con_t = calcular_resumen(d)
        total_con_t = resumen_con_t.totales.total_neto

        assert total_sin_t == total_con_t, (
            f"Tipo T afecto total_neto: sin_T={total_sin_t}, con_T={total_con_t}"
        )


def test_resumen_todos_tipos_neutros_juntos_no_afectan_neto() -> None:
    """ADV-RES-02d: P + N + T juntos no modifican total_neto respecto solo a I."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        _crear_xml_ingreso(d)
        resumen_solo_i = calcular_resumen(d)
        neto_solo_i = resumen_solo_i.totales.total_neto

        _crear_xml_pago(d)
        _crear_xml_nomina(d)
        _crear_xml_traslado(d)
        resumen_con_pnt = calcular_resumen(d)
        neto_con_pnt = resumen_con_pnt.totales.total_neto

        assert neto_solo_i == neto_con_pnt, (
            f"P+N+T modificaron total_neto: solo_I={neto_solo_i}, con_PNT={neto_con_pnt}"
        )


def test_resumen_conteo_tipos_neutros_correcto() -> None:
    """ADV-RES-02e: el conteo de P, N, T en por_tipo es correcto."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        _crear_xml_pago(d)
        _crear_xml_nomina(d)
        _crear_xml_traslado(d)
        resumen = calcular_resumen(d)

        assert resumen.conteo.por_tipo.get("P", 0) == 1
        assert resumen.conteo.por_tipo.get("N", 0) == 1
        assert resumen.conteo.por_tipo.get("T", 0) == 1
        assert resumen.conteo.por_tipo.get("I", 0) == 0
        assert resumen.conteo.por_tipo.get("E", 0) == 0


# ---------------------------------------------------------------------------
# ADV-RES-03: Directorio vacío — exit 0, totales "0.00"
# ---------------------------------------------------------------------------


def test_resumen_directorio_vacio_totales_cero() -> None:
    """ADV-RES-03: directorio sin XMLs → totales en 0, sin error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        resumen = calcular_resumen(d)  # No debe lanzar excepción

        assert resumen.totales.total_neto == Decimal("0"), (
            f"total_neto esperado 0, obtenido {resumen.totales.total_neto}"
        )
        assert resumen.totales.subtotal_ingresos == Decimal("0")
        assert resumen.totales.subtotal_egresos == Decimal("0")


def test_resumen_directorio_vacio_conteo_cero() -> None:
    """ADV-RES-03b: directorio vacío → exitosos=0, errores=0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        resumen = calcular_resumen(d)

        assert resumen.conteo.exitosos == 0
        assert resumen.conteo.errores == 0
        assert resumen.conteo.total_archivos == 0


def test_resumen_directorio_vacio_iva_cero() -> None:
    """ADV-RES-03c: directorio vacío → IVA trasladado 0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        resumen = calcular_resumen(d)
        assert resumen.impuestos.total_iva_trasladado == Decimal("0")


# ---------------------------------------------------------------------------
# ADV-RES-04: Directorio con solo XMLs corruptos — exitosos=0, con_error>0
# ---------------------------------------------------------------------------


def test_resumen_solo_corruptos_no_falla() -> None:
    """ADV-RES-04: directorio con XMLs corruptos → no lanza excepción."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        # Crear 3 XMLs corruptos
        for i in range(3):
            (d / f"corrupto_{i}.xml").write_text(
                "<?xml version='1.0'?><roto><sin_cierre>", encoding="utf-8"
            )
        # No debe lanzar excepción
        resumen = calcular_resumen(d)
        assert resumen is not None


def test_resumen_solo_corruptos_exitosos_cero() -> None:
    """ADV-RES-04b: directorio con solo XMLs corruptos → exitosos == 0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        for i in range(2):
            (d / f"corrupto_{i}.xml").write_text(
                f"<?xml?>ROTO_{i}", encoding="utf-8"
            )
        resumen = calcular_resumen(d)
        assert resumen.conteo.exitosos == 0


def test_resumen_solo_corruptos_errores_mayor_cero() -> None:
    """ADV-RES-04c: directorio con solo XMLs corruptos → errores > 0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        for i in range(2):
            (d / f"corrupto_{i}.xml").write_text(
                f"ESTO NO ES XML {i}", encoding="utf-8"
            )
        resumen = calcular_resumen(d)
        assert resumen.conteo.errores > 0, (
            f"Se esperaban errores > 0 pero errores={resumen.conteo.errores}"
        )


def test_resumen_solo_corruptos_detalle_errores_no_vacio() -> None:
    """ADV-RES-04d: errores_detalle tiene al menos un registro por archivo corrupto."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        (d / "corrupto.xml").write_text("BASURA", encoding="utf-8")
        resumen = calcular_resumen(d)
        assert len(resumen.errores_detalle) > 0, (
            "errores_detalle vacío a pesar de archivo corrupto"
        )


def test_resumen_solo_corruptos_totales_en_cero() -> None:
    """ADV-RES-04e: con solo corruptos, los totales monetarios permanecen en 0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        (d / "corrupto.xml").write_text("<roto", encoding="utf-8")
        resumen = calcular_resumen(d)
        assert resumen.totales.total_neto == Decimal("0")
        assert resumen.totales.subtotal_ingresos == Decimal("0")
        assert resumen.totales.subtotal_egresos == Decimal("0")


# ---------------------------------------------------------------------------
# ADV-RES-05: Directorio inexistente → DirectorioNoEncontradoError
# ---------------------------------------------------------------------------


def test_resumen_directorio_inexistente_lanza_error() -> None:
    """ADV-RES-05: directorio que no existe → DirectorioNoEncontradoError."""
    from contiinia.errors import DirectorioNoEncontradoError

    with pytest.raises(DirectorioNoEncontradoError):
        calcular_resumen(Path("/tmp/dir_adversarial_no_existe_xyz_123"))


# ---------------------------------------------------------------------------
# ADV-RES-06: Mezcla de corruptos y válidos — solo válidos suman
# ---------------------------------------------------------------------------


def test_resumen_mezcla_validos_y_corruptos() -> None:
    """ADV-RES-06: corruptos no abortan el proceso; válidos se acumulan."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        _crear_xml_ingreso(d, "ingreso.xml")
        (d / "corrupto.xml").write_text("<xml corrupto sin cerrar", encoding="utf-8")
        resumen = calcular_resumen(d)

        assert resumen.conteo.exitosos == 1
        assert resumen.conteo.errores == 1
        assert resumen.totales.total_neto == Decimal("1160.00")


def test_resumen_mezcla_cfdi33_y_validos() -> None:
    """ADV-RES-06b: un CFDI 3.3 en el lote no aborta; se cuenta como error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)
        _crear_xml_ingreso(d, "ingreso_valido.xml")
        # Copiar el fixture 3.3 al directorio temporal
        import shutil
        shutil.copy(
            FIXTURES / "cfdi_3.3_rechazado.xml",
            d / "cfdi_33.xml",
        )
        resumen = calcular_resumen(d)

        # El 3.3 debe contar como error, no abortar
        assert resumen.conteo.exitosos == 1
        assert resumen.conteo.errores == 1
        # El total solo considera el válido
        assert resumen.totales.total_neto == Decimal("1160.00")

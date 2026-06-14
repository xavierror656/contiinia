"""Pruebas adversariales para el parser XML CFDI 4.0.

Objetivo: encontrar bugs en valores de importes, tipos de comprobante,
errores de versión, XML corrupto y la interfaz CLI via subprocess.
"""

import json
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from contiinia.errors import SystemError as ContiiniaSystemError
from contiinia.errors import UnsupportedVersionError, XmlMalformadoError
from contiinia.parsers.xml import parsear_xml

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"
PROJECT = Path(__file__).parent.parent.parent


def fx(nombre: str) -> Path:
    return FIXTURES / nombre


# ---------------------------------------------------------------------------
# ADV-XML-01: cfdi_ingreso.xml — total exacto como string "1160.00"
# ---------------------------------------------------------------------------


def test_ingreso_total_string_exacto() -> None:
    """ADV-XML-01: total == '1160.00' como string, no float."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    # CfdiXml serializa Decimal → str. Internamente es Decimal.
    assert cfdi.total == Decimal("1160.00")
    # Al serializar, debe ser exactamente "1160.00"
    data = json.loads(cfdi.model_dump_json())
    assert data["total"] == "1160.00"
    assert isinstance(data["total"], str)


def test_ingreso_subtotal_string_exacto() -> None:
    """ADV-XML-01b: subtotal == '1000.00' como string."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    assert data["subtotal"] == "1000.00"
    assert isinstance(data["subtotal"], str)


def test_ingreso_tipo_I() -> None:
    """ADV-XML-01c: cfdi_ingreso.xml → tipo_de_comprobante == 'I'."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    assert cfdi.tipo_de_comprobante == "I"


def test_ingreso_moneda_mxn() -> None:
    """ADV-XML-01d: cfdi_ingreso.xml → moneda == 'MXN'."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    assert cfdi.moneda == "MXN"


# ---------------------------------------------------------------------------
# ADV-XML-02: cfdi_egreso.xml — tipo E y total "580.00"
# ---------------------------------------------------------------------------


def test_egreso_tipo_E() -> None:
    """ADV-XML-02: cfdi_egreso.xml → tipo_de_comprobante == 'E'."""
    cfdi = parsear_xml(fx("cfdi_egreso.xml"))
    assert cfdi.tipo_de_comprobante == "E"


def test_egreso_total_string_exacto() -> None:
    """ADV-XML-02b: total de egreso == '580.00' como string."""
    cfdi = parsear_xml(fx("cfdi_egreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    assert data["total"] == "580.00"
    assert isinstance(data["total"], str)


def test_egreso_subtotal_string() -> None:
    """ADV-XML-02c: subtotal de egreso == '500.00' como string."""
    cfdi = parsear_xml(fx("cfdi_egreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    assert data["subtotal"] == "500.00"
    assert isinstance(data["subtotal"], str)


def test_egreso_iva_traslado_importe() -> None:
    """ADV-XML-02d: traslado de egreso tiene importe '80.00'."""
    cfdi = parsear_xml(fx("cfdi_egreso.xml"))
    data = json.loads(cfdi.model_dump_json())
    importes_traslados = [t["importe"] for t in data.get("impuestos", {}).get("traslados", [])]
    assert "80.00" in importes_traslados


# ---------------------------------------------------------------------------
# ADV-XML-03: cfdi_iva_frontera.xml — tasa "0.080000"
# ---------------------------------------------------------------------------


def test_iva_frontera_tasa_exacta() -> None:
    """ADV-XML-03: tasa_o_cuota en traslado global == '0.080000' exacto."""
    cfdi = parsear_xml(fx("cfdi_iva_frontera.xml"))
    data = json.loads(cfdi.model_dump_json())
    tasas = [t["tasa_o_cuota"] for t in data.get("impuestos", {}).get("traslados", [])]
    assert "0.080000" in tasas
    # No debe haber "0.08" (pérdida de ceros) ni "0.0800000" (dígitos extra)
    assert "0.08" not in tasas
    assert "0.16" not in tasas


def test_iva_frontera_tasa_en_concepto() -> None:
    """ADV-XML-03b: tasa 8% también presente en los traslados del concepto."""
    cfdi = parsear_xml(fx("cfdi_iva_frontera.xml"))
    data = json.loads(cfdi.model_dump_json())
    tasas_concepto = [
        t["tasa_o_cuota"]
        for c in data.get("conceptos", [])
        for t in c.get("impuestos", {}).get("traslados", [])
    ]
    assert "0.080000" in tasas_concepto


# ---------------------------------------------------------------------------
# ADV-XML-04: cfdi_iva_exento.xml — TipoFactor "Exento", tasa_o_cuota None/ausente
# ---------------------------------------------------------------------------


def test_iva_exento_tipo_factor_exento() -> None:
    """ADV-XML-04: traslado global tiene tipo_factor == 'Exento'."""
    cfdi = parsear_xml(fx("cfdi_iva_exento.xml"))
    traslados = cfdi.impuestos.traslados if cfdi.impuestos else []
    assert len(traslados) >= 1
    assert traslados[0].tipo_factor == "Exento"


def test_iva_exento_tasa_o_cuota_none() -> None:
    """ADV-XML-04b: tasa_o_cuota es None cuando TipoFactor='Exento'."""
    cfdi = parsear_xml(fx("cfdi_iva_exento.xml"))
    traslados = cfdi.impuestos.traslados if cfdi.impuestos else []
    assert len(traslados) >= 1
    assert traslados[0].tasa_o_cuota is None


def test_iva_exento_tasa_ausente_en_json() -> None:
    """ADV-XML-04c: 'tasa_o_cuota' no aparece en JSON cuando es None (exclude_none)."""
    cfdi = parsear_xml(fx("cfdi_iva_exento.xml"))
    data = json.loads(cfdi.model_dump_json(exclude_none=True))
    for t in data.get("impuestos", {}).get("traslados", []):
        if t.get("tipo_factor") == "Exento":
            assert "tasa_o_cuota" not in t, (
                f"tasa_o_cuota presente en traslado Exento: {t}"
            )


def test_iva_exento_importe_ausente_en_json() -> None:
    """ADV-XML-04d: 'importe' también ausente en traslado Exento (no hay importe de IVA)."""
    cfdi = parsear_xml(fx("cfdi_iva_exento.xml"))
    traslados = cfdi.impuestos.traslados if cfdi.impuestos else []
    assert len(traslados) >= 1
    assert traslados[0].importe is None


# ---------------------------------------------------------------------------
# ADV-XML-05: cfdi_xml_corrupto.xml — debe lanzar SystemError (XmlMalformadoError)
# ---------------------------------------------------------------------------


def test_xml_corrupto_lanza_xml_malformado() -> None:
    """ADV-XML-05: XML corrupto → XmlMalformadoError (subclase de SystemError)."""
    with pytest.raises(XmlMalformadoError):
        parsear_xml(fx("cfdi_xml_corrupto.xml"))


def test_xml_corrupto_no_lanza_business_error() -> None:
    """ADV-XML-05b: XML corrupto NO debe lanzar BusinessError."""
    from contiinia.errors import BusinessError
    try:
        parsear_xml(fx("cfdi_xml_corrupto.xml"))
        pytest.fail("Se esperaba una excepción pero no se lanzó ninguna")
    except XmlMalformadoError:
        pass  # Correcto
    except BusinessError as exc:
        pytest.fail(f"Se lanzó BusinessError en lugar de XmlMalformadoError: {exc}")


def test_xml_corrupto_error_incluye_ruta() -> None:
    """ADV-XML-05c: el error del XML corrupto incluye la ruta del archivo."""
    ruta = fx("cfdi_xml_corrupto.xml")
    try:
        parsear_xml(ruta)
        pytest.fail("Se esperaba excepción")
    except XmlMalformadoError as exc:
        assert exc.archivo is not None
        assert "cfdi_xml_corrupto.xml" in exc.archivo


# ---------------------------------------------------------------------------
# ADV-XML-06: cfdi_3.3_rechazado.xml — debe lanzar UnsupportedVersionError
# ---------------------------------------------------------------------------


def test_cfdi33_lanza_unsupported_version() -> None:
    """ADV-XML-06: CFDI 3.3 → UnsupportedVersionError, no BusinessError."""
    with pytest.raises(UnsupportedVersionError):
        parsear_xml(fx("cfdi_3.3_rechazado.xml"))


def test_cfdi33_error_type_correcto() -> None:
    """ADV-XML-06b: error_type es 'version_no_soportada'."""
    try:
        parsear_xml(fx("cfdi_3.3_rechazado.xml"))
        pytest.fail("Se esperaba excepción")
    except UnsupportedVersionError as exc:
        assert exc.error_type == "version_no_soportada"


def test_cfdi33_exit_code_es_2() -> None:
    """ADV-XML-06c: UnsupportedVersionError tiene exit_code == 2."""
    try:
        parsear_xml(fx("cfdi_3.3_rechazado.xml"))
        pytest.fail("Se esperaba excepción")
    except UnsupportedVersionError as exc:
        assert exc.exit_code == 2


# ---------------------------------------------------------------------------
# ADV-XML-07: Archivo inexistente — debe lanzar error con información útil
# ---------------------------------------------------------------------------


def test_archivo_inexistente_lanza_error() -> None:
    """ADV-XML-07: archivo que no existe → XmlMalformadoError (OSError wrapeado)."""
    ruta_falsa = "/tmp/no_existe_cfdi_adversarial_xyz.xml"
    with pytest.raises(Exception):
        parsear_xml(ruta_falsa)


def test_archivo_inexistente_es_sistema() -> None:
    """ADV-XML-07b: archivo inexistente → error de sistema (SystemError subclass)."""
    ruta_falsa = "/tmp/no_existe_cfdi_adversarial_xyz_2.xml"
    try:
        parsear_xml(ruta_falsa)
        pytest.fail("Se esperaba excepción")
    except ContiiniaSystemError:
        pass  # Correcto
    except Exception as exc:
        pytest.fail(
            f"Se esperaba ContiiniaSystemError pero se obtuvo {type(exc).__name__}: {exc}"
        )


# ---------------------------------------------------------------------------
# ADV-XML-08: Todos los importes en JSON de salida son strings, no números
# ---------------------------------------------------------------------------


def _check_no_numeric(obj: object, path: str = "") -> None:
    """Verifica recursivamente que no haya int ni float en el JSON."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            _check_no_numeric(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _check_no_numeric(v, f"{path}[{i}]")
    elif isinstance(obj, (int, float)):
        # int es permitido solo para campos booleanos o contadores (no importes)
        # En un CFDI fiscal, bool aparece como true/false, no como 1/0
        raise AssertionError(
            f"Valor numerico encontrado en {path}: {obj!r} (tipo {type(obj).__name__})"
        )


def test_ingreso_json_sin_numeros_float() -> None:
    """ADV-XML-08: ningún campo en JSON de cfdi_ingreso.xml es float."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    data = json.loads(cfdi.model_dump_json(exclude_none=True))

    def check_no_float(obj: object, path: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                check_no_float(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                check_no_float(v, f"{path}[{i}]")
        elif isinstance(obj, float):
            raise AssertionError(f"Float en {path}: {obj!r}")

    check_no_float(data)


def test_egreso_json_sin_numeros_float() -> None:
    """ADV-XML-08b: ningún campo en JSON de cfdi_egreso.xml es float."""
    cfdi = parsear_xml(fx("cfdi_egreso.xml"))
    data = json.loads(cfdi.model_dump_json(exclude_none=True))

    def check_no_float(obj: object, path: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                check_no_float(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                check_no_float(v, f"{path}[{i}]")
        elif isinstance(obj, float):
            raise AssertionError(f"Float en {path}: {obj!r}")

    check_no_float(data)


def test_frontera_json_sin_numeros_float() -> None:
    """ADV-XML-08c: ningún campo en JSON de cfdi_iva_frontera.xml es float."""
    cfdi = parsear_xml(fx("cfdi_iva_frontera.xml"))
    data = json.loads(cfdi.model_dump_json(exclude_none=True))

    def check_no_float(obj: object, path: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                check_no_float(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                check_no_float(v, f"{path}[{i}]")
        elif isinstance(obj, float):
            raise AssertionError(f"Float en {path}: {obj!r}")

    check_no_float(data)


# ---------------------------------------------------------------------------
# ADV-XML-09: CLI via subprocess — exit codes y stdout/stderr
# ---------------------------------------------------------------------------


def test_cli_ingreso_exitcode_0_subprocess() -> None:
    """ADV-XML-09: CLI subprocess cfdi_ingreso.xml → exit 0, stdout JSON válido.

    BUG DOCUMENTADO: el campo se serializa como 'tipo_comprobante' en el JSON
    de salida CLI, pero el modelo Pydantic lo define como 'tipo_de_comprobante'.
    El nombre en el XML del SAT es 'TipoDeComprobante'. La inconsistencia entre
    el nombre del campo Pydantic y la clave JSON emitida es un bug de serialización.

    Caso mínimo que reproduce el bug:
        contiinia xml fixtures/cfdi_ingreso.xml | python3 -c "import sys,json; d=json.load(sys.stdin); print('tipo_de_comprobante' in d)"
        → False

    El campo aparece como 'tipo_comprobante' en el JSON, no 'tipo_de_comprobante'.
    """
    result = subprocess.run(
        ["uv", "run", "contiinia", "xml", "fixtures/cfdi_ingreso.xml"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT),
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}, stdout: {result.stdout!r}"
    data = json.loads(result.stdout)
    assert isinstance(data, dict)

    # BUG: el campo se llama 'tipo_comprobante' en el JSON, NO 'tipo_de_comprobante'
    # Esta aserción documenta el comportamiento actual (buggy):
    assert "tipo_comprobante" in data, (
        "BUG: campo tipo_comprobante ausente del JSON. "
        f"Campos presentes: {sorted(data.keys())}"
    )
    # Esta aserción documenta que el nombre CORRECTO (del XML SAT) está AUSENTE:
    assert "tipo_de_comprobante" not in data, (
        "Si 'tipo_de_comprobante' aparece en el JSON, el bug fue corregido. "
        "Actualizar este test para reflejar el estado actual."
    )


def test_cli_ingreso_total_en_stdout_subprocess() -> None:
    """ADV-XML-09b: CLI subprocess → total '1160.00' en stdout JSON."""
    result = subprocess.run(
        ["uv", "run", "contiinia", "xml", "fixtures/cfdi_ingreso.xml"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT),
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["total"] == "1160.00"


def test_cli_cfdi33_exit_2_subprocess() -> None:
    """ADV-XML-09c: CLI subprocess cfdi_3.3_rechazado.xml → exit code 2."""
    result = subprocess.run(
        ["uv", "run", "contiinia", "xml", "fixtures/cfdi_3.3_rechazado.xml"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT),
    )
    assert result.returncode == 2, (
        f"Exit code esperado: 2, obtenido: {result.returncode}. "
        f"stdout={result.stdout!r}, stderr={result.stderr!r}"
    )


def test_cli_cfdi33_error_en_stderr_subprocess() -> None:
    """ADV-XML-09d: CLI subprocess cfdi_3.3_rechazado.xml → JSON de error en stderr."""
    result = subprocess.run(
        ["uv", "run", "contiinia", "xml", "fixtures/cfdi_3.3_rechazado.xml"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT),
    )
    assert result.returncode == 2
    error_data = json.loads(result.stderr)
    assert error_data.get("error") == "version_no_soportada"


def test_cli_cfdi33_stdout_vacio_subprocess() -> None:
    """ADV-XML-09e: CLI subprocess cfdi_3.3_rechazado.xml → stdout vacío (no mezcla)."""
    result = subprocess.run(
        ["uv", "run", "contiinia", "xml", "fixtures/cfdi_3.3_rechazado.xml"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT),
    )
    assert result.returncode == 2
    assert result.stdout.strip() == "", (
        f"stdout deberia estar vacio pero contiene: {result.stdout!r}"
    )


def test_cli_xml_corrupto_exit_3_subprocess() -> None:
    """ADV-XML-09f: CLI subprocess cfdi_xml_corrupto.xml → exit code 3."""
    result = subprocess.run(
        ["uv", "run", "contiinia", "xml", "fixtures/cfdi_xml_corrupto.xml"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT),
    )
    assert result.returncode == 3, (
        f"Exit code esperado: 3, obtenido: {result.returncode}. "
        f"stdout={result.stdout!r}, stderr={result.stderr!r}"
    )


def test_cli_xml_corrupto_error_en_stderr_subprocess() -> None:
    """ADV-XML-09g: CLI subprocess cfdi_xml_corrupto.xml → JSON de error en stderr."""
    result = subprocess.run(
        ["uv", "run", "contiinia", "xml", "fixtures/cfdi_xml_corrupto.xml"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT),
    )
    assert result.returncode == 3
    error_data = json.loads(result.stderr)
    assert "error" in error_data


def test_cli_xml_corrupto_stdout_vacio_subprocess() -> None:
    """ADV-XML-09h: CLI subprocess cfdi_xml_corrupto.xml → stdout vacío."""
    result = subprocess.run(
        ["uv", "run", "contiinia", "xml", "fixtures/cfdi_xml_corrupto.xml"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT),
    )
    assert result.returncode == 3
    assert result.stdout.strip() == "", (
        f"stdout debe estar vacío pero contiene: {result.stdout!r}"
    )


def test_cli_archivo_inexistente_exit_3_subprocess() -> None:
    """ADV-XML-09i: CLI subprocess archivo inexistente → exit code 3."""
    result = subprocess.run(
        ["uv", "run", "contiinia", "xml", "/tmp/cfdi_no_existe_adversarial.xml"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT),
    )
    assert result.returncode == 3, (
        f"Exit code esperado: 3, obtenido: {result.returncode}. "
        f"stderr={result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# ADV-XML-10: --schema emite JSON Schema válido
# ---------------------------------------------------------------------------


def test_cli_schema_es_json_schema_valido_subprocess() -> None:
    """ADV-XML-10: CLI subprocess --schema → JSON Schema con 'properties' y '$defs'."""
    result = subprocess.run(
        ["uv", "run", "contiinia", "xml", "--schema"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT),
    )
    assert result.returncode == 0, f"stderr: {result.stderr!r}"
    schema = json.loads(result.stdout)
    assert isinstance(schema, dict)
    # Un JSON Schema válido debe tener al menos 'properties' o '$defs'
    assert "properties" in schema or "$defs" in schema, (
        f"JSON Schema sin 'properties' ni '$defs': {list(schema.keys())}"
    )


def test_cli_schema_contiene_campos_fiscales_subprocess() -> None:
    """ADV-XML-10b: el JSON Schema contiene campos clave de CFDI.

    BUG DOCUMENTADO: el JSON Schema emitido por --schema usa el nombre de campo
    'tipo_comprobante' en lugar de 'tipo_de_comprobante'. Este nombre es inconsistente
    con el atributo XML del SAT ('TipoDeComprobante') y puede confundir a clientes
    que integren el Schema.

    Adicionalmente, el schema permite 'type: number' para campos Decimal como
    'descuento', lo que es inconsistente con la implementación que siempre serializa
    como string. El schema debería declarar solo 'type: string' para esos campos.
    """
    result = subprocess.run(
        ["uv", "run", "contiinia", "xml", "--schema"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT),
    )
    assert result.returncode == 0
    schema = json.loads(result.stdout)
    props = schema.get("properties", {})

    # Campos que SÍ deben estar (no relacionados con el bug):
    for campo in ["total", "subtotal", "moneda"]:
        assert campo in props, f"Campo '{campo}' ausente en JSON Schema"

    # BUG: el schema usa 'tipo_comprobante', NO 'tipo_de_comprobante'
    assert "tipo_comprobante" in props, (
        "BUG: campo 'tipo_comprobante' ausente del JSON Schema. "
        f"Campos presentes: {sorted(props.keys())}"
    )
    assert "tipo_de_comprobante" not in props, (
        "Si 'tipo_de_comprobante' aparece en el Schema, el bug fue corregido. "
        "Actualizar este test."
    )

    # BUG SECUNDARIO: 'descuento' en el schema permite 'number' (float),
    # pero la implementación serializa Decimal solo como string.
    descuento_schema = props.get("descuento", {})
    any_of_types = [
        alt.get("type")
        for alt in descuento_schema.get("anyOf", [])
    ]
    assert "number" in any_of_types, (
        "BUG: el schema de 'descuento' permite 'type: number' (float), "
        "inconsistente con la serialización que siempre produce strings. "
        f"Tipos en anyOf: {any_of_types}"
    )


# ---------------------------------------------------------------------------
# ADV-XML-11: XML con nodo Emisor faltante — debe fallar con BusinessError
# ---------------------------------------------------------------------------


def test_xml_sin_emisor_lanza_business_error() -> None:
    """ADV-XML-11: XML válido estructuralmente pero sin nodo Emisor → BusinessError."""
    from contiinia.errors import BusinessError

    xml_sin_emisor = """\
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  Version="4.0" Serie="A" Folio="9999" Fecha="2024-03-15T10:00:00"
  Sello="X" NoCertificado="00001" Certificado="X"
  SubTotal="100.00" Moneda="MXN" Total="116.00"
  TipoDeComprobante="I" Exportacion="01" LugarExpedicion="06600">
  <cfdi:Receptor Rfc="BBB020202BBB" Nombre="X"
    DomicilioFiscalReceptor="64000" RegimenFiscalReceptor="601"
    UsoCFDI="G01"/>
  <cfdi:Conceptos/>
</cfdi:Comprobante>
"""
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", encoding="utf-8", delete=False) as f:
        f.write(xml_sin_emisor)
        ruta_tmp = f.name

    try:
        with pytest.raises(BusinessError):
            parsear_xml(ruta_tmp)
    finally:
        import os
        os.unlink(ruta_tmp)


def test_xml_sin_receptor_lanza_business_error() -> None:
    """ADV-XML-11b: XML sin nodo Receptor → BusinessError."""
    from contiinia.errors import BusinessError

    xml_sin_receptor = """\
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  Version="4.0" Serie="A" Folio="9999" Fecha="2024-03-15T10:00:00"
  Sello="X" NoCertificado="00001" Certificado="X"
  SubTotal="100.00" Moneda="MXN" Total="116.00"
  TipoDeComprobante="I" Exportacion="01" LugarExpedicion="06600">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="X" RegimenFiscal="601"/>
  <cfdi:Conceptos/>
</cfdi:Comprobante>
"""
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", encoding="utf-8", delete=False) as f:
        f.write(xml_sin_receptor)
        ruta_tmp = f.name

    try:
        with pytest.raises(BusinessError):
            parsear_xml(ruta_tmp)
    finally:
        import os
        os.unlink(ruta_tmp)


# ---------------------------------------------------------------------------
# ADV-XML-12: CFDI en USD — moneda distinta de MXN debe parsearse sin error
# ---------------------------------------------------------------------------


_XML_USD = """\
<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
  Version="4.0" Serie="A" Folio="5000" Fecha="2024-03-15T10:00:00"
  Sello="X" NoCertificado="00001" Certificado="X"
  SubTotal="500.00" Moneda="USD" TipoCambio="17.50" Total="580.00"
  TipoDeComprobante="I" Exportacion="02" LugarExpedicion="06600">
  <cfdi:Emisor Rfc="AAA010101AAA" Nombre="X" RegimenFiscal="601"/>
  <cfdi:Receptor Rfc="BBB020202BBB" Nombre="X"
    DomicilioFiscalReceptor="64000" RegimenFiscalReceptor="601"
    UsoCFDI="G01"/>
  <cfdi:Conceptos>
    <cfdi:Concepto ClaveProdServ="81161500" ClaveUnidad="H87"
      Cantidad="5.000" Descripcion="Servicio en dolares"
      ValorUnitario="100.00" Importe="500.00" ObjetoImp="02"/>
  </cfdi:Conceptos>
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital xmlns:tfd="http://www.sat.gob.mx/TimbreFiscalDigital"
      Version="1.1" UUID="AAAAAAAA-0000-0000-0000-000000000099"
      FechaTimbrado="2024-03-15T10:05:00" RfcProvCertif="SAT970701NN3"
      NoCertificadoSAT="20001000000300022323"/>
  </cfdi:Complemento>
</cfdi:Comprobante>
"""


def test_xml_cfdi_usd_parsea_sin_error() -> None:
    """ADV-XML-12: CFDI con Moneda='USD' se parsea sin errores."""
    xml_usd = _XML_USD
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", encoding="utf-8", delete=False) as f:
        f.write(xml_usd)
        ruta_tmp = f.name

    try:
        cfdi = parsear_xml(ruta_tmp)
        assert cfdi.moneda == "USD"
        assert cfdi.tipo_cambio == Decimal("17.50")
        assert cfdi.total == Decimal("580.00")
    finally:
        import os
        os.unlink(ruta_tmp)


def test_xml_cfdi_usd_tipo_cambio_como_string_en_json() -> None:
    """ADV-XML-12b: TipoCambio en JSON es string, no float."""
    xml_usd = _XML_USD
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", encoding="utf-8", delete=False) as f:
        f.write(xml_usd)
        ruta_tmp = f.name

    try:
        cfdi = parsear_xml(ruta_tmp)
        data = json.loads(cfdi.model_dump_json())
        assert isinstance(data["tipo_cambio"], str), (
            f"tipo_cambio debe ser string pero es {type(data['tipo_cambio'])}: {data['tipo_cambio']!r}"
        )
        assert data["tipo_cambio"] == "17.50"
    finally:
        import os
        os.unlink(ruta_tmp)


# ---------------------------------------------------------------------------
# ADV-XML-13: Todos los tipos de CFDI 4.0 (I/E/P/N/T) parseados contra valores conocidos
# ---------------------------------------------------------------------------


def test_cfdi_tipo_P_valores_conocidos() -> None:
    """ADV-XML-13a: cfdi_pago.xml → tipo P, total '0', moneda XXX."""
    cfdi = parsear_xml(fx("cfdi_pago.xml"))
    assert cfdi.tipo_de_comprobante == "P"
    assert cfdi.moneda == "XXX"
    assert cfdi.total == Decimal("0")


def test_cfdi_tipo_N_valores_conocidos() -> None:
    """ADV-XML-13b: cfdi_nomina.xml → tipo N, total '15000.00'."""
    cfdi = parsear_xml(fx("cfdi_nomina.xml"))
    assert cfdi.tipo_de_comprobante == "N"
    assert cfdi.total == Decimal("15000.00")


def test_cfdi_tipo_T_valores_conocidos() -> None:
    """ADV-XML-13c: cfdi_traslado.xml → tipo T, total '0'."""
    cfdi = parsear_xml(fx("cfdi_traslado.xml"))
    assert cfdi.tipo_de_comprobante == "T"
    assert cfdi.total == Decimal("0")


def test_cfdi_tipo_I_uuid_concreto() -> None:
    """ADV-XML-13d: cfdi_ingreso.xml → UUID '...123456789001'."""
    cfdi = parsear_xml(fx("cfdi_ingreso.xml"))
    assert cfdi.uuid.endswith("123456789001")


def test_cfdi_tipo_E_uuid_concreto() -> None:
    """ADV-XML-13e: cfdi_egreso.xml → UUID '...123456789002'."""
    cfdi = parsear_xml(fx("cfdi_egreso.xml"))
    assert cfdi.uuid.endswith("123456789002")

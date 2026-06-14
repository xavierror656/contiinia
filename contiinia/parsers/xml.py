"""Parser de CFDI 4.0 XML — Hito 4.4."""

from decimal import Decimal, InvalidOperation
from pathlib import Path

from lxml import etree

from contiinia.errors import (
    ArchivoNoEncontradoError,
    BusinessError,
    UnsupportedVersionError,
    XmlMalformadoError,
)
from contiinia.models.cfdi import (
    CfdiXml,
    ComplementoTimbre,
    Concepto,
    Emisor,
    Receptor,
    Retencion,
    Traslado,
)

NS4 = "http://www.sat.gob.mx/cfd/4"
NS3 = "http://www.sat.gob.mx/cfd/3"
NS_TFD = "http://www.sat.gob.mx/TimbreFiscalDigital"


def _d(value: str | None) -> Decimal | None:
    """Convierte string a Decimal; None si value es None."""
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        raise BusinessError(f"Importe inválido: {value}")


def parsear_xml(ruta: str | Path) -> CfdiXml:
    """Parsea un CFDI 4.0 XML y retorna CfdiXml. Lanza excepciones tipadas ante errores."""
    ruta = Path(ruta)

    try:
        tree = etree.parse(str(ruta))
    except etree.XMLSyntaxError as exc:
        raise XmlMalformadoError(f"XML malformado: {exc}", archivo=str(ruta)) from exc
    except FileNotFoundError as exc:
        raise ArchivoNoEncontradoError(f"Archivo no encontrado: {ruta}", archivo=str(ruta)) from exc
    except PermissionError as exc:
        raise XmlMalformadoError(f"Sin permisos para leer el archivo: {exc}", archivo=str(ruta)) from exc
    except OSError as exc:
        raise XmlMalformadoError(f"No se pudo leer el archivo: {exc}", archivo=str(ruta)) from exc

    root = tree.getroot()

    # Detectar namespace del elemento raíz
    ns = root.nsmap.get(None) or root.nsmap.get("cfdi", "")

    if NS3 in (ns or ""):
        raise UnsupportedVersionError(
            "CFDI 3.3 no soportado; solo se acepta 4.0",
            archivo=str(ruta),
        )
    if NS4 not in (ns or ""):
        raise UnsupportedVersionError(
            f"Namespace no reconocido: {ns}",
            archivo=str(ruta),
        )

    def tag(name: str) -> str:
        return f"{{{NS4}}}{name}"

    def attr(el: etree._Element, name: str, required: bool = False) -> str | None:
        v = el.get(name)
        if required and v is None:
            raise BusinessError(
                f"Atributo requerido faltante: {name}",
                archivo=str(ruta),
            )
        return v

    # Emisor
    em_el = root.find(tag("Emisor"))
    if em_el is None:
        raise BusinessError("Nodo Emisor faltante", archivo=str(ruta))
    emisor = Emisor(
        rfc=attr(em_el, "Rfc", required=True),
        nombre=attr(em_el, "Nombre"),
        regimen_fiscal=attr(em_el, "RegimenFiscal", required=True),
    )

    # Receptor
    rec_el = root.find(tag("Receptor"))
    if rec_el is None:
        raise BusinessError("Nodo Receptor faltante", archivo=str(ruta))
    receptor = Receptor(
        rfc=attr(rec_el, "Rfc", required=True),
        nombre=attr(rec_el, "Nombre"),
        domicilio_fiscal_receptor=attr(rec_el, "DomicilioFiscalReceptor"),
        residencia_fiscal=attr(rec_el, "ResidenciaFiscal"),
        num_reg_id_trib=attr(rec_el, "NumRegIdTrib"),
        regimen_fiscal_receptor=attr(rec_el, "RegimenFiscalReceptor"),
        uso_cfdi=attr(rec_el, "UsoCFDI", required=True),
    )

    # Conceptos
    conceptos: list[Concepto] = []
    for c_el in root.findall(f"{tag('Conceptos')}/{tag('Concepto')}"):
        traslados: list[Traslado] = []
        for t_el in c_el.findall(
            f"{tag('Impuestos')}/{tag('Traslados')}/{tag('Traslado')}"
        ):
            traslados.append(
                Traslado(
                    impuesto=attr(t_el, "Impuesto", required=True),
                    tipo_factor=attr(t_el, "TipoFactor", required=True),
                    tasa_o_cuota=_d(attr(t_el, "TasaOCuota")),
                    base=_d(attr(t_el, "Base")),
                    importe=_d(attr(t_el, "Importe")),
                )
            )
        retenciones: list[Retencion] = []
        for r_el in c_el.findall(
            f"{tag('Impuestos')}/{tag('Retenciones')}/{tag('Retencion')}"
        ):
            retenciones.append(
                Retencion(
                    impuesto=attr(r_el, "Impuesto", required=True),
                    importe=_d(attr(r_el, "Importe")),
                )
            )
        conceptos.append(
            Concepto(
                clave_prod_serv=attr(c_el, "ClaveProdServ", required=True),
                no_identificacion=attr(c_el, "NoIdentificacion"),
                cantidad=_d(attr(c_el, "Cantidad")),
                clave_unidad=attr(c_el, "ClaveUnidad", required=True),
                unidad=attr(c_el, "Unidad"),
                descripcion=attr(c_el, "Descripcion", required=True),
                valor_unitario=_d(attr(c_el, "ValorUnitario")),
                importe=_d(attr(c_el, "Importe")),
                descuento=_d(attr(c_el, "Descuento")),
                objeto_imp=attr(c_el, "ObjetoImp"),
                traslados=traslados,
                retenciones=retenciones,
            )
        )

    # Impuestos globales
    imp_el = root.find(tag("Impuestos"))
    traslados_globales: list[Traslado] = []
    retenciones_globales: list[Retencion] = []
    total_trasladados = None
    total_retenidos = None
    if imp_el is not None:
        total_trasladados = _d(attr(imp_el, "TotalImpuestosTrasladados"))
        total_retenidos = _d(attr(imp_el, "TotalImpuestosRetenidos"))
        for t_el in imp_el.findall(f"{tag('Traslados')}/{tag('Traslado')}"):
            traslados_globales.append(
                Traslado(
                    impuesto=attr(t_el, "Impuesto", required=True),
                    tipo_factor=attr(t_el, "TipoFactor", required=True),
                    tasa_o_cuota=_d(attr(t_el, "TasaOCuota")),
                    base=_d(attr(t_el, "Base")),
                    importe=_d(attr(t_el, "Importe")),
                )
            )
        for r_el in imp_el.findall(f"{tag('Retenciones')}/{tag('Retencion')}"):
            retenciones_globales.append(
                Retencion(
                    impuesto=attr(r_el, "Impuesto", required=True),
                    importe=_d(attr(r_el, "Importe")),
                )
            )

    # Timbre Fiscal Digital
    timbre = None
    comp_el = root.find(tag("Complemento"))
    if comp_el is not None:
        tfd_el = comp_el.find(f"{{{NS_TFD}}}TimbreFiscalDigital")
        if tfd_el is not None:
            timbre = ComplementoTimbre(
                uuid=attr(tfd_el, "UUID", required=True).upper(),
                fecha_timbrado=attr(tfd_el, "FechaTimbrado", required=True),
                rfc_prov_certif=attr(tfd_el, "RfcProvCertif", required=True),
                no_certificado_sat=attr(tfd_el, "NoCertificadoSAT", required=True),
            )

    return CfdiXml(
        version=attr(root, "Version", required=True),
        serie=attr(root, "Serie"),
        folio=attr(root, "Folio"),
        fecha=attr(root, "Fecha", required=True),
        sello=attr(root, "Sello"),
        forma_pago=attr(root, "FormaPago"),
        no_certificado=attr(root, "NoCertificado", required=True),
        certificado=attr(root, "Certificado"),
        subtotal=_d(attr(root, "SubTotal", required=True)),
        descuento=_d(attr(root, "Descuento")),
        moneda=attr(root, "Moneda", required=True),
        tipo_cambio=_d(attr(root, "TipoCambio")),
        total=_d(attr(root, "Total", required=True)),
        tipo_de_comprobante=attr(root, "TipoDeComprobante", required=True),
        exportacion=attr(root, "Exportacion"),
        metodo_pago=attr(root, "MetodoPago"),
        lugar_expedicion=attr(root, "LugarExpedicion", required=True),
        emisor=emisor,
        receptor=receptor,
        conceptos=conceptos,
        total_impuestos_trasladados=total_trasladados,
        total_impuestos_retenidos=total_retenidos,
        traslados_globales=traslados_globales,
        retenciones_globales=retenciones_globales,
        timbre=timbre,
    )

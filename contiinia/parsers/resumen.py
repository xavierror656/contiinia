"""Parser/agregador para `contiinia resumen` — Hito 4.7."""

from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from contiinia.errors import ContiiniaError, DirectorioNoEncontradoError, RutaNoEsDirectorioError
from contiinia.models.resumen import (
    ErrorDetalle,
    IvaTrasladadoPorTasa,
    PagoPpdSinComplemento,
    ResumenConteo,
    ResumenImpuestos,
    ResumenLote,
    ResumenNomina,
    ResumenPeriodo,
    ResumenTotales,
    ResumenTraslados,
)
from contiinia.parsers.xml import parsear_xml


# Tipos que NO contribuyen al total_neto (subtotal_ingresos / subtotal_egresos)
_TIPOS_NEUTROS = {"P", "N", "T"}


def calcular_resumen(directorio: Path, recursivo: bool = False) -> ResumenLote:
    """Agrega totales fiscales de todos los CFDI 4.0 en *directorio*.

    Reglas fiscales (Principio 8 de la constitución):
    - Tipo I (Ingreso): suma a subtotal_ingresos y contribuye al IVA trasladado.
    - Tipo E (Egreso/nota de crédito): suma a subtotal_egresos y RESTA del IVA trasladado.
    - Tipos P, N, T: neutros; no modifican subtotal_neto ni IVA trasladado.
    - CFDI tipo I con MetodoPago=PPD y sin complemento de pago real: se cuenta en
      pagos_ppd_sin_complemento (el CFDI sí existe, pero el cobro es diferido).
    - Archivos con error van a errores_detalle; no abortan el proceso.
    """
    if not directorio.exists():
        raise DirectorioNoEncontradoError(
            f"Directorio no encontrado: {directorio}",
            archivo=str(directorio),
        )
    if not directorio.is_dir():
        raise RutaNoEsDirectorioError(
            f"La ruta no es un directorio: {directorio}",
            archivo=str(directorio),
        )

    pattern = "**/*.xml" if recursivo else "*.xml"
    archivos = sorted(directorio.glob(pattern))

    # --- Acumuladores ---
    conteo_tipo: dict[str, int] = defaultdict(int)
    # Solo I y E contribuyen a subtotales monetarios
    subtotal_i = Decimal("0")
    subtotal_e = Decimal("0")
    total_i = Decimal("0")
    total_e = Decimal("0")

    # IVA trasladado agregado por (tipo_factor, tasa_o_cuota)
    # clave: (tipo_factor, tasa_o_cuota_str)  — tasa_o_cuota_str puede ser None si Exento
    iva_base: dict[tuple, Decimal] = defaultdict(Decimal)
    iva_importe: dict[tuple, Decimal] = defaultdict(Decimal)

    # Retenciones (IVA e ISR)
    total_iva_retenido = Decimal("0")
    total_isr_retenido = Decimal("0")

    # PPD sin complemento de pago
    ppd_uuids: list[str] = []

    # Nómina
    nomina_count = 0
    nomina_percepciones = Decimal("0")

    # Traslados
    traslado_count = 0

    # Período
    fechas: list[str] = []

    # Errores
    errores_detalle: list[ErrorDetalle] = []
    exitosos = 0

    for archivo in archivos:
        ruta_str = str(archivo)
        try:
            cfdi = parsear_xml(archivo)
        except ContiiniaError as exc:
            errores_detalle.append(
                ErrorDetalle(
                    archivo=ruta_str,
                    error=exc.error_type,
                    detalle=exc.detalle,
                )
            )
            continue
        except Exception as exc:
            errores_detalle.append(
                ErrorDetalle(
                    archivo=ruta_str,
                    error="error_inesperado",
                    detalle=str(exc),
                )
            )
            continue

        exitosos += 1
        tipo = cfdi.tipo_de_comprobante
        conteo_tipo[tipo] += 1

        subtotal = cfdi.subtotal or Decimal("0")
        total = cfdi.total or Decimal("0")

        # Registrar fecha para período
        if cfdi.fecha:
            fechas.append(cfdi.fecha)

        traslados_globales = cfdi.impuestos.traslados if cfdi.impuestos else []
        retenciones_globales = cfdi.impuestos.retenciones if cfdi.impuestos else []

        # --- Contabilización por tipo ---
        if tipo == "I":
            subtotal_i += subtotal
            total_i += total

            # PPD sin complemento de pago real
            if cfdi.metodo_pago == "PPD" and not cfdi.complemento_pago_detectado:
                ppd_uuids.append(cfdi.uuid or ruta_str)

            # IVA trasladado: tipo I suma
            for t in traslados_globales:
                if t.impuesto == "002":  # IVA
                    clave = (t.tipo_factor, str(t.tasa_o_cuota) if t.tasa_o_cuota is not None else None)
                    iva_base[clave] += t.base or Decimal("0")
                    iva_importe[clave] += t.importe or Decimal("0")

            # Retenciones de tipo I
            for r in retenciones_globales:
                if r.impuesto == "002":
                    total_iva_retenido += r.importe or Decimal("0")
                elif r.impuesto == "001":
                    total_isr_retenido += r.importe or Decimal("0")

        elif tipo == "E":
            subtotal_e += subtotal
            total_e += total

            # IVA trasladado: tipo E resta
            for t in traslados_globales:
                if t.impuesto == "002":
                    clave = (t.tipo_factor, str(t.tasa_o_cuota) if t.tasa_o_cuota is not None else None)
                    iva_base[clave] -= t.base or Decimal("0")
                    iva_importe[clave] -= t.importe or Decimal("0")

        elif tipo == "N":
            nomina_count += 1
            # No agregamos percepciones de nómina en v1 (fuera de alcance)

        elif tipo == "T":
            traslado_count += 1

        # Tipo P: neutro, no suma a ningún total monetario

    # --- Construir objeto de salida ---

    # Total neto: I - E (usando Total, no SubTotal)
    subtotal_ingresos = subtotal_i
    subtotal_egresos = subtotal_e
    total_neto = total_i - total_e

    # Conteo por tipo (incluyendo los 5 tipos estándar con 0 si no aparecen)
    por_tipo: dict[str, int] = {
        "I": conteo_tipo.get("I", 0),
        "E": conteo_tipo.get("E", 0),
        "P": conteo_tipo.get("P", 0),
        "N": conteo_tipo.get("N", 0),
        "T": conteo_tipo.get("T", 0),
    }
    # Añadir tipos inesperados si existieran
    for t in conteo_tipo:
        if t not in por_tipo:
            por_tipo[t] = conteo_tipo[t]

    # IVA trasladado por tasa
    iva_por_tasa: list[IvaTrasladadoPorTasa] = []
    for clave in sorted(iva_base.keys(), key=lambda k: (k[0], str(k[1] or ""))):
        tipo_factor, tasa_str = clave
        if tipo_factor == "Exento":
            tasa_display = "Exento"
        else:
            tasa_display = tasa_str or "0.000000"
        iva_por_tasa.append(
            IvaTrasladadoPorTasa(
                tasa=tasa_display,
                base=iva_base[clave],
                importe=iva_importe[clave],
            )
        )

    total_iva_trasladado = sum(
        (v for (tf, _), v in iva_importe.items() if tf != "Exento"),
        Decimal("0"),
    )

    # Período
    fecha_min = min(fechas) if fechas else None
    fecha_max = max(fechas) if fechas else None

    return ResumenLote(
        directorio=str(directorio),
        recursivo=recursivo,
        moneda_base="MXN",
        periodo=ResumenPeriodo(fecha_min=fecha_min, fecha_max=fecha_max),
        conteo=ResumenConteo(
            total_archivos=len(archivos),
            exitosos=exitosos,
            errores=len(errores_detalle),
            por_tipo=por_tipo,
        ),
        totales=ResumenTotales(
            subtotal_ingresos=subtotal_ingresos,
            subtotal_egresos=subtotal_egresos,
            total_neto=total_neto,
        ),
        impuestos=ResumenImpuestos(
            iva_trasladado_por_tasa=iva_por_tasa,
            total_iva_trasladado=total_iva_trasladado,
            total_iva_retenido=total_iva_retenido,
            total_isr_retenido=total_isr_retenido,
        ),
        pagos_ppd_sin_complemento=PagoPpdSinComplemento(
            count=len(ppd_uuids),
            uuids=ppd_uuids,
        ),
        nomina=ResumenNomina(
            count=nomina_count,
            total_percepciones=nomina_percepciones,
            advertencia=(
                "Los totales de nómina requieren complemento de nómina; "
                "valores no agregados en esta versión."
            ),
        ),
        traslados=ResumenTraslados(count=traslado_count),
        errores_detalle=errores_detalle,
        advertencias=[],
    )

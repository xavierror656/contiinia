"""Parser de RFC mexicano — función pura; sin I/O, sin efectos laterales."""

import re
from datetime import date

from contiinia.models.rfc import RfcValidation

# RFC genéricos del SAT (siempre válidos, no pasan por el algoritmo general)
_RFC_GENERICO_NACIONAL = "XAXX010101000"
_RFC_GENERICO_EXTRANJERO = "XEXX010101000"

# Patrones de caracteres permitidos en las letras iniciales del RFC
_LETRAS_RFC = r"[A-ZÑ&]"

# Patrón persona moral: 3 letras + 6 dígitos + 3 alfanuméricos = 12 chars
_PATRON_MORAL = re.compile(
    rf"^{_LETRAS_RFC}{{3}}[0-9]{{6}}[A-Z0-9]{{3}}$",
    re.UNICODE,
)

# Patrón persona física: 4 letras + 6 dígitos + 3 alfanuméricos = 13 chars
_PATRON_FISICA = re.compile(
    rf"^{_LETRAS_RFC}{{4}}[0-9]{{6}}[A-Z0-9]{{3}}$",
    re.UNICODE,
)

# Sólo caracteres alfanuméricos y Ñ y & (para detección rápida de chars inválidos)
_PATRON_CHARS_VALIDOS = re.compile(r"^[A-ZÑ&0-9]+$", re.UNICODE)


def _fecha_valida(digits: str) -> bool:
    """Verifica que los 6 dígitos AAMMDD formen una fecha calendario válida.

    AA = año de 2 dígitos (00-99 mapeado a 1900-1999 o 2000-2099 según contexto).
    Se acepta tanto siglo XX como XXI. No se verifica que sea futura aquí.
    """
    aa = int(digits[0:2])
    mm = int(digits[2:4])
    dd = int(digits[4:6])

    if mm < 1 or mm > 12:
        return False
    if dd < 1 or dd > 31:
        return False

    # Intentar construir la fecha en ambos siglos posibles
    for century in (2000, 1900):
        year = century + aa
        try:
            date(year, mm, dd)
            return True
        except ValueError:
            continue
    return False


def _fecha_futura(digits: str) -> bool:
    """Devuelve True si la fecha del RFC es posterior a hoy (en cualquier siglo)."""
    aa = int(digits[0:2])
    mm = int(digits[2:4])
    dd = int(digits[4:6])
    hoy = date.today()

    # Intentar construir la fecha prefiriendo el siglo más reciente que dé una fecha válida
    for century in (2000, 1900):
        year = century + aa
        try:
            fecha = date(year, mm, dd)
            if fecha > hoy:
                return True
            return False
        except ValueError:
            continue
    return False


def validar_rfc(rfc: str) -> RfcValidation:
    """Valida la estructura formal de un RFC mexicano.

    Reglas aplicadas (en orden de prioridad):
    1. Normalización a mayúsculas.
    2. Detección de guiones/espacios → caracteres_invalidos.
    3. Longitud: 12 (moral) o 13 (física) → longitud_incorrecta si no cumple.
    4. RFC genérico del SAT → válido directamente.
    5. Caracteres permitidos ([A-ZÑ&0-9]) → caracteres_invalidos.
    6. Patrón estructural (letras iniciales + fecha dígitos + homoclave) → caracteres_invalidos.
    7. Fecha válida → fecha_invalida.
    8. Fecha futura → fecha_futura.

    QA-RFC-01 (decisión provisional): se normaliza a mayúsculas antes de validar.
    """
    # --- 1. Normalizar a mayúsculas (QA-RFC-01: decisión provisional = aceptar minúsculas)
    rfc_upper = rfc.upper()

    # --- 2. Guiones o espacios → rechazo inmediato con caracter_invalido
    if "-" in rfc or " " in rfc:
        return RfcValidation(rfc=rfc_upper, valido=False, motivo="caracteres_invalidos")

    # --- 3. Validar longitud
    longitud = len(rfc_upper)
    if longitud not in (12, 13):
        return RfcValidation(rfc=rfc_upper, valido=False, motivo="longitud_incorrecta")

    # --- 4. RFC genéricos del SAT (bypass de todas las demás validaciones)
    if rfc_upper == _RFC_GENERICO_NACIONAL:
        return RfcValidation(
            rfc=rfc_upper,
            valido=True,
            tipo="generico_nacional",
            longitud=longitud,
        )
    if rfc_upper == _RFC_GENERICO_EXTRANJERO:
        return RfcValidation(
            rfc=rfc_upper,
            valido=True,
            tipo="generico_extranjero",
            longitud=longitud,
        )

    # --- 5. Verificar que todos los caracteres sean del alfabeto permitido
    if not _PATRON_CHARS_VALIDOS.match(rfc_upper):
        return RfcValidation(rfc=rfc_upper, valido=False, motivo="caracteres_invalidos")

    # --- 6. Verificar patrón estructural según longitud
    if longitud == 12:
        patron = _PATRON_MORAL
        tipo = "moral"
        fecha_offset = 3
    else:
        patron = _PATRON_FISICA
        tipo = "fisica"
        fecha_offset = 4

    if not patron.match(rfc_upper):
        return RfcValidation(rfc=rfc_upper, valido=False, motivo="caracteres_invalidos")

    # --- 7. Validar fecha (los 6 dígitos después de las letras iniciales)
    digits_fecha = rfc_upper[fecha_offset : fecha_offset + 6]
    if not _fecha_valida(digits_fecha):
        return RfcValidation(rfc=rfc_upper, valido=False, motivo="fecha_invalida")

    # --- 8. Verificar que la fecha no sea futura
    if _fecha_futura(digits_fecha):
        return RfcValidation(rfc=rfc_upper, valido=False, motivo="fecha_futura")

    return RfcValidation(rfc=rfc_upper, valido=True, tipo=tipo, longitud=longitud)

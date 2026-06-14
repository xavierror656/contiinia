"""Parser de RFC mexicano — función pura; sin I/O, sin efectos laterales."""

import re
from datetime import date

from contiinia.models.rfc import RfcValidation

# RFC genéricos del SAT (siempre válidos, no pasan por el algoritmo general)
_RFC_GENERICO_NACIONAL = "XAXX010101000"
_RFC_GENERICO_EXTRANJERO = "XEXX010101000"

# Alfabeto para cálculo del dígito verificador (CA-RFC-08).
# Fuente: SAT Anexo 20 / python-stdnum mx/rfc.py (LGPL, Arthur de Jong).
# Orden: 0-9, A-N, &, O-Z, espacio, Ñ  (&=24, espacio=37, Ñ=38)
_ALFABETO_DIGITO = "0123456789ABCDEFGHIJKLMN&OPQRSTUVWXYZ Ñ"


def _digito_verificador(rfc_sin_ultimo: str) -> str:
    """Calcula el dígito verificador esperado del RFC.

    rfc_sin_ultimo: RFC en mayúsculas sin el último carácter (el dígito a verificar).
    Rellena con espacio a la izquierda hasta 12 posiciones y aplica la suma ponderada mod 11.
    """
    padded = ("   " + rfc_sin_ultimo)[-12:]
    check = sum(_ALFABETO_DIGITO.index(c) * (13 - i) for i, c in enumerate(padded))
    return _ALFABETO_DIGITO[(11 - check) % 11]

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
    """Devuelve True solo si AMBOS siglos posibles producen una fecha futura.

    Si alguno de los dos siglos produce una fecha pasada/presente válida, el
    RFC se acepta (beneficio de la duda: un RFC de 1980 tiene aa=80, que en
    el siglo XXI sería 2080, pero en el siglo XX es 1980 — válido).
    """
    aa = int(digits[0:2])
    mm = int(digits[2:4])
    dd = int(digits[4:6])
    hoy = date.today()

    fechas_validas: list[date] = []
    for century in (2000, 1900):
        try:
            fechas_validas.append(date(century + aa, mm, dd))
        except ValueError:
            continue

    if not fechas_validas:
        return False
    # Solo futura si TODAS las fechas válidas son futuras
    return all(f > hoy for f in fechas_validas)


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

    QA-RFC-01: se normaliza a mayúsculas antes de validar (minúsculas aceptadas).
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

    # --- 9. Validar dígito verificador (CA-RFC-08)
    if rfc_upper[-1] != _digito_verificador(rfc_upper[:-1]):
        return RfcValidation(rfc=rfc_upper, valido=False, motivo="digito_verificador_incorrecto")

    return RfcValidation(rfc=rfc_upper, valido=True, tipo=tipo, longitud=longitud)

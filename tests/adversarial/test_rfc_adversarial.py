"""Pruebas adversariales para el parser RFC.

Objetivo: encontrar bugs en edge cases no cubiertos por los tests existentes.
Estrategia: inputs que desafían las fronteras del regex, la normalización
y la lógica de fecha.

Todos los RFCs "válidos" en estas pruebas tienen dígito verificador correcto
(verificado con el algoritmo SAT Anexo 20, fuente: python-stdnum mx/rfc.py).
"""

import pytest

from contiinia.parsers.rfc import validar_rfc


# ---------------------------------------------------------------------------
# ADV-RFC-01: RFC con Ñ en posición inicial de persona moral (3 letras)
# ---------------------------------------------------------------------------


def test_rfc_n_tilde_persona_moral_posicion_0() -> None:
    """ADV-RFC-01: RFC con Ñ y año ambiguo (80) → válido con siglo 1900 (1980-01-01).

    ÑOÑO800101AA1 es un RFC de persona física válido con 13 chars.
    La fecha en posición [4:10] es '800101' → año=80, mes=01, día=01.
    - Siglo 2000: 2080-01-01 → FUTURO
    - Siglo 1900: 1980-01-01 → PASADO (válido)

    _fecha_futura solo rechaza si TODOS los siglos posibles dan fecha futura.
    Como 1980 es pasado, el RFC debe aceptarse.
    Dígito verificador correcto = '1' (verificado).
    """
    rfc = "ÑOÑO800101AA1"
    assert len(rfc) == 13

    result = validar_rfc(rfc)

    assert result.valido is True, (
        f"REGRESIÓN BUG-02: {rfc} debería ser válido (1980-01-01 es pasado). "
        f"Resultado: {result}"
    )
    assert result.tipo == "fisica"


def test_rfc_bug_fecha_futura_siglo_ambiguo_caso_minimo() -> None:
    """ADV-RFC-01: caso mínimo — AAA800101AA3 (moral) con año ambiguo 80 → válido.

    - Siglo 2000: 2080-01-01 → FUTURO
    - Siglo 1900: 1980-01-01 → PASADO (válido)

    _fecha_futura solo retorna True si TODOS los siglos dan fecha futura.
    Como 1980 es pasado, el RFC debe aceptarse.
    Dígito verificador correcto = '3' (verificado).
    """
    result = validar_rfc("AAA800101AA3")
    assert result.valido is True, (
        f"REGRESIÓN BUG-02: AAA800101AA3 debería ser válido (1980-01-01 es pasado). "
        f"Resultado: {result}"
    )
    assert result.tipo == "moral"


def test_rfc_n_tilde_persona_moral_3_letras() -> None:
    """ADV-RFC-01b: ÑAÑ (3 letras con Ñ) como moral — 12 chars."""
    # ÑAÑ010101AA1: dígito verificador correcto = '1' (verificado)
    rfc = "ÑAÑ010101AA1"
    assert len(rfc) == 12
    result = validar_rfc(rfc)
    assert result.valido is True
    assert result.tipo == "moral"


def test_rfc_n_tilde_inicio_fisica_4_letras() -> None:
    """ADV-RFC-01c: ÑOÑO como 4 letras iniciales de persona física."""
    # ÑOÑO010101AAA: dígito verificador correcto = 'A' (verificado)
    rfc = "ÑOÑO010101AAA"
    assert len(rfc) == 13
    result = validar_rfc(rfc)
    assert result.valido is True
    assert result.tipo == "fisica"


# ---------------------------------------------------------------------------
# ADV-RFC-02: RFC con & (ampersand) — persona moral de 12 chars
# ---------------------------------------------------------------------------


def test_rfc_ampersand_posicion_1_moral() -> None:
    """ADV-RFC-02: & en posición 1 de una moral de 12 chars — debe ser válido."""
    # A&A010101AA1: dígito verificador correcto = '1' (verificado)
    rfc = "A&A010101AA1"
    assert len(rfc) == 12
    result = validar_rfc(rfc)
    assert result.valido is True
    assert result.tipo == "moral"


def test_rfc_ampersand_en_homoclave_invalido() -> None:
    """ADV-RFC-02b: & en la homoclave (posiciones finales) — debe fallar.

    La homoclave solo acepta [A-Z0-9], no & ni Ñ.
    """
    # AAA010101A&A: & en posición 10 (dentro de la homoclave)
    rfc = "AAA010101A&A"
    assert len(rfc) == 12
    result = validar_rfc(rfc)
    # La homoclave es [A-Z0-9]{3}, & no está permitida ahí
    assert result.valido is False
    assert result.motivo == "caracteres_invalidos"


def test_rfc_ampersand_en_fecha_invalido() -> None:
    """ADV-RFC-02c: & en la posición de fecha — debe fallar."""
    # AAA&10101AAA: & en posición 3 (donde empieza la fecha)
    rfc = "AAA&10101AAA"
    assert len(rfc) == 12
    result = validar_rfc(rfc)
    assert result.valido is False


# ---------------------------------------------------------------------------
# ADV-RFC-03: RFC todo numérico en posiciones de letras iniciales
# ---------------------------------------------------------------------------


def test_rfc_numericos_en_letras_iniciales_moral() -> None:
    """ADV-RFC-03: dígitos en las primeras 3 posiciones de moral — debe fallar."""
    rfc = "123010101AAA"
    assert len(rfc) == 12
    result = validar_rfc(rfc)
    # El patrón moral requiere [A-ZÑ&]{3} iniciales, los dígitos no cumplen
    assert result.valido is False
    assert result.motivo == "caracteres_invalidos"


def test_rfc_numericos_en_letras_iniciales_fisica() -> None:
    """ADV-RFC-03b: dígitos en las primeras 4 posiciones de física — debe fallar."""
    rfc = "1234010101AAA"
    assert len(rfc) == 13
    result = validar_rfc(rfc)
    assert result.valido is False
    assert result.motivo == "caracteres_invalidos"


# ---------------------------------------------------------------------------
# ADV-RFC-04: RFC con longitud 12 pero dígitos en primeras posiciones
# ---------------------------------------------------------------------------


def test_rfc_ceros_iniciales_longitud_12() -> None:
    """ADV-RFC-04: '000010101AAA' — ceros donde deben ir letras en moral."""
    rfc = "000010101AAA"
    assert len(rfc) == 12
    result = validar_rfc(rfc)
    assert result.valido is False
    assert result.motivo == "caracteres_invalidos"


# ---------------------------------------------------------------------------
# ADV-RFC-05: RFCs genéricos del SAT — XAXX y XEXX
# ---------------------------------------------------------------------------


def test_rfc_generico_xaxx_valido() -> None:
    """ADV-RFC-05: XAXX010101000 — genérico nacional, bypass completo."""
    result = validar_rfc("XAXX010101000")
    assert result.valido is True
    assert result.tipo == "generico_nacional"
    assert result.longitud == 13


def test_rfc_generico_xexx_valido() -> None:
    """ADV-RFC-05b: XEXX010101000 — genérico extranjero."""
    result = validar_rfc("XEXX010101000")
    assert result.valido is True
    assert result.tipo == "generico_extranjero"
    assert result.longitud == 13


def test_rfc_generico_xaxx_en_minusculas() -> None:
    """ADV-RFC-05c: 'xaxx010101000' en minúsculas — debe normalizarse y ser genérico nacional."""
    result = validar_rfc("xaxx010101000")
    assert result.valido is True
    assert result.tipo == "generico_nacional"
    assert result.rfc == "XAXX010101000"


def test_rfc_xaxx_fecha_distinta_invalido() -> None:
    """ADV-RFC-05d: XAXX con fecha diferente a 010101 NO es genérico — valida dígito.

    XAXX010102000 no es el genérico exacto, pasa por validación normal.
    Dígito verificador correcto = '0' (verificado).
    """
    # XAXX010102000 — diferente en el día (02 en vez de 01), NO es genérico exacto
    rfc = "XAXX010102000"
    result = validar_rfc(rfc)
    # Persona física (13 chars): XAXX → 4 letras, 010102 fecha, 000 homoclave
    # Dígito verificador correcto = '0' → válido
    assert result.valido is True
    assert result.tipo == "fisica"
    assert result.tipo != "generico_nacional"


# ---------------------------------------------------------------------------
# ADV-RFC-06: RFC en minúsculas — normalización a mayúsculas
# ---------------------------------------------------------------------------


def test_rfc_minusculas_moral_normalizado() -> None:
    """ADV-RFC-06: 'sat970701nn3' en minúsculas → válido, rfc normalizado."""
    result = validar_rfc("sat970701nn3")
    assert result.valido is True
    assert result.rfc == "SAT970701NN3"
    assert result.tipo == "moral"


def test_rfc_minusculas_fisica_normalizado() -> None:
    """ADV-RFC-06b: 'gode561231gr8' (13 chars) en minúsculas → válido, tipo física."""
    result = validar_rfc("gode561231gr8")
    assert result.valido is True
    assert result.rfc == "GODE561231GR8"
    assert result.tipo == "fisica"


def test_rfc_mixcase_normalizado() -> None:
    """ADV-RFC-06c: 'SaT970701nN3' — mezcla de mayúsculas y minúsculas."""
    result = validar_rfc("SaT970701nN3")
    assert result.valido is True
    assert result.rfc == "SAT970701NN3"


# ---------------------------------------------------------------------------
# ADV-RFC-07: RFC vacío — debe fallar con longitud_incorrecta
# ---------------------------------------------------------------------------


def test_rfc_vacio_falla() -> None:
    """ADV-RFC-07: '' (cadena vacía) → inválido, motivo longitud_incorrecta."""
    result = validar_rfc("")
    assert result.valido is False
    assert result.motivo == "longitud_incorrecta"


def test_rfc_solo_espacios_falla() -> None:
    """ADV-RFC-07b: '   ' (solo espacios) → inválido, motivo caracteres_invalidos."""
    result = validar_rfc("   ")
    assert result.valido is False
    # Espacios detectados en check de guiones/espacios, o longitud incorrecta
    assert result.motivo in ("caracteres_invalidos", "longitud_incorrecta")


# ---------------------------------------------------------------------------
# ADV-RFC-08: RFC con espacios en diferentes posiciones
# ---------------------------------------------------------------------------


def test_rfc_espacios_en_medio() -> None:
    """ADV-RFC-08: 'AAA 010101 AAA' → inválido, caracteres_invalidos."""
    result = validar_rfc("AAA 010101 AAA")
    assert result.valido is False
    assert result.motivo == "caracteres_invalidos"


def test_rfc_espacio_inicial() -> None:
    """ADV-RFC-08b: ' SAT970701NN3' — espacio al inicio."""
    result = validar_rfc(" SAT970701NN3")
    assert result.valido is False
    assert result.motivo == "caracteres_invalidos"


def test_rfc_espacio_final() -> None:
    """ADV-RFC-08c: 'SAT970701NN3 ' — espacio al final."""
    result = validar_rfc("SAT970701NN3 ")
    assert result.valido is False
    assert result.motivo == "caracteres_invalidos"


# ---------------------------------------------------------------------------
# ADV-RFC-09: Fechas imposibles adicionales (calendario gregoriano)
# ---------------------------------------------------------------------------


def test_rfc_30_de_febrero_imposible() -> None:
    """ADV-RFC-09: fecha '000230' (feb 30) → fecha_invalida."""
    result = validar_rfc("AAA000230AAA")
    assert result.valido is False
    assert result.motivo == "fecha_invalida"


def test_rfc_29_feb_no_bisiesto() -> None:
    """ADV-RFC-09b: '010229' en año no bisiesto (2001) → fecha_invalida.

    2001 no es bisiesto; 1901 tampoco. Ambos siglos fallan.
    """
    result = validar_rfc("AAA010229AAA")
    assert result.valido is False
    assert result.motivo == "fecha_invalida"


def test_rfc_fecha_mes_13() -> None:
    """ADV-RFC-09c: mes '13' → fecha_invalida."""
    result = validar_rfc("AAA991399AAA")
    assert result.valido is False
    assert result.motivo == "fecha_invalida"


def test_rfc_fecha_dia_00() -> None:
    """ADV-RFC-09d: día '00' → fecha_invalida."""
    result = validar_rfc("AAA010100AAA")
    assert result.valido is False
    assert result.motivo == "fecha_invalida"


# ---------------------------------------------------------------------------
# ADV-RFC-10: Homoclave válida con números
# ---------------------------------------------------------------------------


def test_rfc_homoclave_con_numeros() -> None:
    """ADV-RFC-10: homoclave alfanumérica — dígito verificador correcto."""
    # AAA0101011A6: dígito verificador correcto = '6' (verificado)
    result = validar_rfc("AAA0101011A6")
    assert result.valido is True
    assert result.tipo == "moral"


def test_rfc_homoclave_todo_numeros() -> None:
    """ADV-RFC-10b: homoclave '120' (solo dígitos) — debe ser válido."""
    # AAA010101120: dígito verificador correcto = '0' (verificado)
    result = validar_rfc("AAA010101120")
    assert result.valido is True
    assert result.tipo == "moral"


# ---------------------------------------------------------------------------
# ADV-RFC-11: Comprobación de campos en resultado
# ---------------------------------------------------------------------------


def test_rfc_valido_contiene_tipo_y_longitud() -> None:
    """ADV-RFC-11: RFC válido debe tener tipo y longitud en el resultado."""
    result = validar_rfc("SAT970701NN3")
    assert result.tipo is not None
    assert result.longitud is not None
    assert result.motivo is None


def test_rfc_invalido_no_tiene_tipo_ni_longitud() -> None:
    """ADV-RFC-11b: RFC inválido — tipo y longitud deben ser None."""
    result = validar_rfc("INVALIDO")
    assert result.valido is False
    # tipo y longitud solo se populan cuando valido=True
    assert result.tipo is None
    assert result.longitud is None


def test_rfc_normalizacion_preserva_n_tilde() -> None:
    """ADV-RFC-11c: la Ñ minúscula (ñ) se normaliza a Ñ mayúscula correctamente."""
    # ÑAÑA010101AAA: dígito verificador correcto = 'A' (verificado)
    rfc_lower = "ñaña010101aaa"  # 13 chars con ñ minúscula
    result = validar_rfc(rfc_lower)
    assert result.rfc == "ÑAÑA010101AAA"
    assert result.valido is True
    assert result.tipo == "fisica"


# ---------------------------------------------------------------------------
# ADV-RFC-12: dígito verificador incorrecto (CA-RFC-08)
# ---------------------------------------------------------------------------


def test_rfc_digito_verificador_incorrecto_moral() -> None:
    """ADV-RFC-12: RFC moral con dígito verificador incorrecto → rechazado."""
    # AAA010101AAA: dígito esperado='1', tiene 'A' → incorrecto
    result = validar_rfc("AAA010101AAA")
    assert result.valido is False
    assert result.motivo == "digito_verificador_incorrecto"


def test_rfc_digito_verificador_incorrecto_fisica() -> None:
    """ADV-RFC-12b: RFC física con dígito verificador incorrecto → rechazado."""
    # AAAA010101AAA: dígito esperado='0', tiene 'A' → incorrecto
    result = validar_rfc("AAAA010101AAA")
    assert result.valido is False
    assert result.motivo == "digito_verificador_incorrecto"


def test_rfc_digito_verificador_orden_validaciones() -> None:
    """ADV-RFC-12c: fecha inválida tiene prioridad sobre dígito verificador incorrecto."""
    # Fecha '991399' (mes 13) → falla en fecha_invalida antes de llegar al dígito
    result = validar_rfc("AAA991399AAA")
    assert result.valido is False
    assert result.motivo == "fecha_invalida"

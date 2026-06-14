"""Pruebas unitarias para parsers/rfc.py — cubre CA-RFC-01 a CA-RFC-08."""

import pytest

from contiinia.parsers.rfc import validar_rfc


# ---------------------------------------------------------------------------
# Casos válidos
# ---------------------------------------------------------------------------


def test_rfc_generico_nacional() -> None:
    """CA-RFC-01: XAXX010101000 → válido, tipo generico_nacional."""
    result = validar_rfc("XAXX010101000")
    assert result.valido is True
    assert result.tipo == "generico_nacional"
    assert result.rfc == "XAXX010101000"
    assert result.motivo is None


def test_rfc_generico_extranjero() -> None:
    """CA-RFC-02: XEXX010101000 → válido, tipo generico_extranjero."""
    result = validar_rfc("XEXX010101000")
    assert result.valido is True
    assert result.tipo == "generico_extranjero"
    assert result.rfc == "XEXX010101000"
    assert result.motivo is None


def test_rfc_persona_fisica_valido() -> None:
    """CA-RFC-03: RFC de persona física con 13 caracteres válidos."""
    result = validar_rfc("AAAA010101AAA")
    assert result.valido is True
    assert result.tipo == "fisica"
    assert result.longitud == 13
    assert result.motivo is None


def test_rfc_persona_moral_valido() -> None:
    """CA-RFC-04: RFC de persona moral con 12 caracteres válidos."""
    result = validar_rfc("AAA010101AAA")
    assert result.valido is True
    assert result.tipo == "moral"
    assert result.longitud == 12
    assert result.motivo is None


def test_rfc_con_n_valido() -> None:
    """RFC con Ñ en la parte de letras iniciales (persona física, 4 letras)."""
    # ÑOÑO tiene 4 letras: Ñ O Ñ O — estructura persona física si tiene 13 chars total
    result = validar_rfc("ÑAÑA010101AAA")
    assert result.valido is True
    assert result.tipo == "fisica"


def test_rfc_con_ampersand_valido() -> None:
    """RFC con & (ampersand) en la parte de letras (persona moral)."""
    result = validar_rfc("A&A010101AAA")
    assert result.valido is True
    assert result.tipo == "moral"


def test_rfc_persona_moral_homoclave_numerica() -> None:
    """Homoclave con dígitos: AAA0101011A2 (persona moral)."""
    result = validar_rfc("AAA0101011A2")
    assert result.valido is True
    assert result.tipo == "moral"


def test_rfc_minusculas_normalizado() -> None:
    """QA-RFC-01 (decisión provisional): minúsculas se normalizan a mayúsculas."""
    result = validar_rfc("aaa010101aaa")
    assert result.valido is True
    assert result.rfc == "AAA010101AAA"
    assert result.tipo == "moral"


# ---------------------------------------------------------------------------
# Casos inválidos — longitud
# ---------------------------------------------------------------------------


def test_rfc_muy_corto() -> None:
    """CA-RFC-05: longitud distinta de 12 o 13 → longitud_incorrecta."""
    result = validar_rfc("AAA")
    assert result.valido is False
    assert result.motivo == "longitud_incorrecta"


def test_rfc_longitud_11() -> None:
    """RFC de 11 caracteres → longitud_incorrecta."""
    result = validar_rfc("AAA010101AA")
    assert result.valido is False
    assert result.motivo == "longitud_incorrecta"


def test_rfc_longitud_14() -> None:
    """RFC de 14 caracteres → longitud_incorrecta."""
    result = validar_rfc("AAAA010101AAAA")
    assert result.valido is False
    assert result.motivo == "longitud_incorrecta"


# ---------------------------------------------------------------------------
# Casos inválidos — caracteres
# ---------------------------------------------------------------------------


def test_rfc_con_guion() -> None:
    """CA-RFC-06: guiones → caracteres_invalidos."""
    result = validar_rfc("AAA-010101-AAA")
    assert result.valido is False
    assert result.motivo == "caracteres_invalidos"


def test_rfc_con_espacio() -> None:
    """CA-RFC-06: espacios → caracteres_invalidos."""
    result = validar_rfc("AAA 010101 AAA")
    assert result.valido is False
    assert result.motivo == "caracteres_invalidos"


def test_rfc_con_caracteres_especiales() -> None:
    """CA-RFC-06: caracteres especiales (@, #) → caracteres_invalidos."""
    result = validar_rfc("AAA@10101AAA")
    assert result.valido is False
    assert result.motivo == "caracteres_invalidos"


def test_rfc_letras_donde_deberian_ir_numeros() -> None:
    """CA-RFC-06: letras en posición de fecha → caracteres_invalidos."""
    result = validar_rfc("AAAABCDEFAAA")  # 12 chars pero BCDEF en posición de fecha
    assert result.valido is False
    assert result.motivo == "caracteres_invalidos"


# ---------------------------------------------------------------------------
# Casos inválidos — fecha
# ---------------------------------------------------------------------------


def test_rfc_fecha_mes_invalido() -> None:
    """CA-RFC-07: mes 13 → fecha_invalida."""
    result = validar_rfc("AAA991399AAA")
    assert result.valido is False
    assert result.motivo == "fecha_invalida"


def test_rfc_fecha_dia_invalido() -> None:
    """CA-RFC-07: día 32 → fecha_invalida."""
    result = validar_rfc("AAA010132AAA")
    assert result.valido is False
    assert result.motivo == "fecha_invalida"


def test_rfc_fecha_dia_cero() -> None:
    """CA-RFC-07: día 00 → fecha_invalida."""
    result = validar_rfc("AAA010100AAA")
    assert result.valido is False
    assert result.motivo == "fecha_invalida"


def test_rfc_fecha_mes_cero() -> None:
    """CA-RFC-07: mes 00 → fecha_invalida."""
    result = validar_rfc("AAA990001AAA")
    assert result.valido is False
    assert result.motivo == "fecha_invalida"


def test_rfc_fecha_febrero_invalida() -> None:
    """CA-RFC-07: 30 de febrero → fecha_invalida."""
    result = validar_rfc("AAA000230AAA")
    assert result.valido is False
    assert result.motivo == "fecha_invalida"


# ---------------------------------------------------------------------------
# Casos inválidos — fecha futura
# ---------------------------------------------------------------------------


def test_rfc_fecha_futura() -> None:
    """RFC con fecha futura → fecha_futura."""
    # Año 2099, mes 12, día 31 — siempre futuro
    result = validar_rfc("AAA991231AAA")
    assert result.valido is False
    assert result.motivo == "fecha_futura"


# ---------------------------------------------------------------------------
# Salida JSON — estructura
# ---------------------------------------------------------------------------


def test_rfc_valido_json_no_contiene_motivo() -> None:
    """Un RFC válido no debe incluir el campo motivo en el JSON serializado."""
    result = validar_rfc("AAA010101AAA")
    json_str = result.model_dump_json(exclude_none=True)
    assert "motivo" not in json_str


def test_rfc_invalido_json_no_contiene_tipo() -> None:
    """Un RFC inválido no debe incluir el campo tipo en el JSON serializado."""
    result = validar_rfc("AAA")
    json_str = result.model_dump_json(exclude_none=True)
    assert "tipo" not in json_str


def test_rfc_invalido_json_no_contiene_longitud() -> None:
    """Un RFC inválido no debe incluir el campo longitud (como clave) en el JSON serializado."""
    result = validar_rfc("AAA")
    data = result.model_dump(exclude_none=True)
    assert "longitud" not in data

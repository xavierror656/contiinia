"""Pruebas adversariales para Feature 3: IVA estimado por fila.

Cubre CA-TAB-22..28 y casos adversariales de tasa como entero.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from contiinia.models.tabla import AdvertenciaTasaNoNumerica
from contiinia.parsers.tabla import parsear_tabla


def _csv_to_path(contenido: str, tmp_path: Path, nombre: str = "tabla.csv") -> Path:
    ruta = tmp_path / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


# ---------------------------------------------------------------------------
# CA-TAB-22: sin columna tasa → iva_estimado ausente de registros
# ---------------------------------------------------------------------------


def test_sin_columna_tasa_iva_estimado_ausente_de_registros(tmp_path: Path) -> None:
    """CA-TAB-22: sin columna tasa → iva_estimado NO aparece en el JSON de cada registro."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,1.000000,10000.00,10000.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    # Verificar en JSON
    data = json.loads(result.model_dump_json(exclude_none=True))
    for reg in data["registros"]:
        assert "iva_estimado" not in reg, (
            f"iva_estimado no debería aparecer sin columna tasa, pero está en fila {reg['fila']}"
        )


def test_sin_columna_tasa_total_iva_estimado_ausente(tmp_path: Path) -> None:
    """CA-TAB-22: sin columna tasa → total_iva_estimado NO aparece en TablaResult."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,1.000000,10000.00,10000.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    assert result.total_iva_estimado is None
    data = json.loads(result.model_dump_json(exclude_none=True))
    assert "total_iva_estimado" not in data, "total_iva_estimado no debe aparecer sin columna tasa"


def test_sin_columna_tasa_sin_advertencias_tasa(tmp_path: Path) -> None:
    """CA-TAB-22: sin columna tasa → no hay advertencias de tipo tasa_no_numerica."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe\n"
        "84111506,Servicio,1.000000,10000.00,10000.00\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    adv_tasa = [
        a for a in result.advertencias
        if isinstance(a, AdvertenciaTasaNoNumerica)
    ]
    assert adv_tasa == []


# ---------------------------------------------------------------------------
# CA-TAB-23: columna tasa_iva → mapeada como tasa, IVA calculado
# ---------------------------------------------------------------------------


def test_columna_tasa_iva_mapeada(tmp_path: Path) -> None:
    """CA-TAB-23: columna 'tasa_iva' mapeada a 'tasa', iva_estimado calculado."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa_iva\n"
        "84111506,Servicio,1.000000,10000.00,10000.00,0.160000\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    assert "tasa" in result.columnas_detectadas, "tasa_iva debe mapearse a 'tasa'"
    assert result.registros[0].iva_estimado == Decimal("10000.00") * Decimal("0.160000")


def test_columna_tasa_iva_aparece_en_json(tmp_path: Path) -> None:
    """CA-TAB-23: con tasa_iva, iva_estimado aparece en JSON del registro."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa_iva\n"
        "84111506,Servicio,1.000000,10000.00,10000.00,0.160000\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    data = json.loads(result.model_dump_json())
    assert "iva_estimado" in data["registros"][0]


# ---------------------------------------------------------------------------
# CA-TAB-24: importe=10000, tasa=0.160000 → iva_estimado="1600.00"
# ---------------------------------------------------------------------------


def test_iva_calculado_160000(tmp_path: Path) -> None:
    """CA-TAB-24: importe=10000, tasa=0.160000 → iva_estimado=1600.00."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Servicio,1.000000,10000.00,10000.00,0.160000\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    assert result.registros[0].iva_estimado == Decimal("1600.0000")


def test_iva_calculado_string_en_json(tmp_path: Path) -> None:
    """CA-TAB-24 + CA-TAB-28: iva_estimado es string en JSON, no number."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Servicio,1.000000,10000.00,10000.00,0.160000\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    data = json.loads(result.model_dump_json())
    iva = data["registros"][0]["iva_estimado"]
    assert isinstance(iva, str), f"iva_estimado debe ser string, es: {type(iva)}: {iva!r}"
    assert not isinstance(iva, float)


def test_iva_calculado_valor_correcto_string(tmp_path: Path) -> None:
    """CA-TAB-24: el string de iva_estimado representa '1600.0000' (producto exacto)."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Servicio,1.000000,10000.00,10000.00,0.160000\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    data = json.loads(result.model_dump_json())
    iva_str = data["registros"][0]["iva_estimado"]
    # El valor en Decimal debe ser equivalente a 1600
    assert Decimal(iva_str) == Decimal("1600.0000")


# ---------------------------------------------------------------------------
# CA-TAB-25: importe=500, tasa=0.000000 → iva_estimado="0.00"
# ---------------------------------------------------------------------------


def test_tasa_cero_iva_cero(tmp_path: Path) -> None:
    """CA-TAB-25: tasa=0.000000 → iva_estimado=Decimal('0.000000')."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Exento,1.000000,500.00,500.00,0.000000\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    assert result.registros[0].iva_estimado == Decimal("0")


def test_tasa_cero_iva_es_string_en_json(tmp_path: Path) -> None:
    """CA-TAB-25: iva_estimado=0 debe ser string '0.000000' en JSON, no null ni number."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Exento,1.000000,500.00,500.00,0.000000\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    data = json.loads(result.model_dump_json())
    iva = data["registros"][0]["iva_estimado"]
    assert iva is not None, "iva_estimado=0 no debe ser null"
    assert isinstance(iva, str), f"iva_estimado=0 debe ser string, es: {type(iva)}"
    assert Decimal(iva) == Decimal("0")


# ---------------------------------------------------------------------------
# CA-TAB-26: tasa="Exento" → iva_estimado=null, advertencia tasa_no_numerica
# ---------------------------------------------------------------------------


def test_tasa_exento_iva_null(tmp_path: Path) -> None:
    """CA-TAB-26: tasa='Exento' → iva_estimado=null."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Exento,1.000000,500.00,500.00,Exento\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    assert result.registros[0].iva_estimado is None


def test_tasa_exento_genera_advertencia(tmp_path: Path) -> None:
    """CA-TAB-26: tasa='Exento' → advertencia tipo tasa_no_numerica."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Exento,1.000000,500.00,500.00,Exento\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    adv_tasa = [
        a for a in result.advertencias
        if isinstance(a, AdvertenciaTasaNoNumerica)
    ]
    assert len(adv_tasa) == 1


def test_tasa_exento_advertencia_fila(tmp_path: Path) -> None:
    """CA-TAB-26: advertencia tasa_no_numerica tiene fila=2."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Exento,1.000000,500.00,500.00,Exento\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    adv = next(
        a for a in result.advertencias
        if isinstance(a, AdvertenciaTasaNoNumerica)
    )
    assert adv.fila == 2


def test_tasa_exento_advertencia_valor_encontrado(tmp_path: Path) -> None:
    """CA-TAB-26: advertencia tasa_no_numerica tiene valor_encontrado='Exento'."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Exento,1.000000,500.00,500.00,Exento\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    adv = next(
        a for a in result.advertencias
        if isinstance(a, AdvertenciaTasaNoNumerica)
    )
    assert adv.valor_encontrado == "Exento"


def test_tasa_na_iva_null_con_advertencia(tmp_path: Path) -> None:
    """CA-TAB-26: tasa='N/A' → misma lógica que 'Exento'."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Exento,1.000000,500.00,500.00,N/A\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    assert result.registros[0].iva_estimado is None
    adv_tasa = [
        a for a in result.advertencias
        if isinstance(a, AdvertenciaTasaNoNumerica)
    ]
    assert len(adv_tasa) == 1
    assert adv_tasa[0].valor_encontrado == "N/A"


def test_tasa_exento_otras_filas_calculadas_normalmente(tmp_path: Path) -> None:
    """CA-TAB-26: fila con Exento no afecta el cálculo de otras filas."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Normal,1.000000,10000.00,10000.00,0.160000\n"
        "84111507,Exento,1.000000,500.00,500.00,Exento\n"
        "84111508,Normal2,1.000000,2000.00,2000.00,0.160000\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    assert result.registros[0].iva_estimado == Decimal("1600.0000")
    assert result.registros[1].iva_estimado is None
    assert result.registros[2].iva_estimado == Decimal("320.0000")


# ---------------------------------------------------------------------------
# CA-TAB-27: total_iva_estimado es suma exacta de iva_estimado no nulos
# ---------------------------------------------------------------------------


def test_total_iva_suma_exacta(tmp_path: Path) -> None:
    """CA-TAB-27: total_iva_estimado es la suma de iva_estimado no nulos."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Servicio A,1.000000,10000.00,10000.00,0.160000\n"
        "84111507,Servicio B,1.000000,2000.00,2000.00,0.160000\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    # iva fila 1: 10000 * 0.16 = 1600
    # iva fila 2: 2000 * 0.16 = 320
    # total = 1920
    assert result.total_iva_estimado == Decimal("1920.0000")


def test_total_iva_excluye_nulos(tmp_path: Path) -> None:
    """CA-TAB-27: total_iva_estimado excluye filas con iva_estimado=null."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Normal,1.000000,10000.00,10000.00,0.160000\n"
        "84111507,Exento,1.000000,500.00,500.00,Exento\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    # Solo la fila 1 aporta: 10000 * 0.16 = 1600
    assert result.total_iva_estimado == Decimal("1600.0000")


def test_total_iva_todos_nulos_es_cero(tmp_path: Path) -> None:
    """CA-TAB-27: si todos los iva son null, total_iva_estimado='0.00' (no null)."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Exento,1.000000,500.00,500.00,Exento\n"
        "84111507,NA,1.000000,200.00,200.00,N/A\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    # total_iva_estimado debe existir (columna tasa presente) y ser 0
    assert result.total_iva_estimado is not None
    assert result.total_iva_estimado == Decimal("0")


# ---------------------------------------------------------------------------
# CA-TAB-28: iva_estimado y total_iva_estimado nunca son number JSON
# ---------------------------------------------------------------------------


def test_iva_estimado_no_es_number_json(tmp_path: Path) -> None:
    """CA-TAB-28: iva_estimado en JSON es string, nunca number."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Servicio,1.000000,10000.00,10000.00,0.160000\n"
        "84111507,Servicio2,1.000000,2000.00,2000.00,0.080000\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    data = json.loads(result.model_dump_json())
    for reg in data["registros"]:
        iva = reg.get("iva_estimado")
        if iva is not None:
            assert isinstance(iva, str), f"iva_estimado debe ser str en JSON, es {type(iva)}: {iva!r}"
            assert not isinstance(iva, (int, float))


def test_total_iva_estimado_no_es_number_json(tmp_path: Path) -> None:
    """CA-TAB-28: total_iva_estimado en JSON es string, nunca number."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Servicio,1.000000,10000.00,10000.00,0.160000\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    data = json.loads(result.model_dump_json())
    total = data.get("total_iva_estimado")
    assert total is not None
    assert isinstance(total, str), f"total_iva_estimado debe ser str en JSON, es {type(total)}: {total!r}"
    assert not isinstance(total, (int, float))


# ---------------------------------------------------------------------------
# Alias: columna "porcentaje" → mapeada a "tasa"
# ---------------------------------------------------------------------------


def test_columna_porcentaje_mapeada_a_tasa(tmp_path: Path) -> None:
    """CA-TAB-28 ext: columna 'porcentaje' → mapeada a 'tasa'."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,porcentaje\n"
        "84111506,Servicio,1.000000,10000.00,10000.00,0.160000\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    assert "tasa" in result.columnas_detectadas
    assert result.registros[0].iva_estimado is not None
    assert result.registros[0].iva_estimado == Decimal("10000.00") * Decimal("0.160000")


# ---------------------------------------------------------------------------
# ADVERSARIAL: tasa=16 (entero) → NO se normaliza, valor aceptado tal cual
# ---------------------------------------------------------------------------


def test_tasa_entero_16_acepta_valor_literal(tmp_path: Path) -> None:
    """ADVERSARIAL CA-TAB-28: tasa=16 (entero en texto) → se toma como Decimal('16'),
    iva_estimado = importe * 16 (NO como 0.16). El sistema no normaliza.
    Documentar si el sistema incorrecto normaliza a 0.16."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Servicio,1.000000,1000.00,1000.00,16\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    # Con tasa=16, el cálculo literalmente es 1000 * 16 = 16000
    # Si el sistema diera 160, estaría normalizando incorrectamente
    assert result.registros[0].iva_estimado == Decimal("16000")


def test_tasa_entero_no_normalizado_en_json(tmp_path: Path) -> None:
    """ADVERSARIAL: verificar que tasa=16 produce iva=16000 y no 160 en JSON."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Servicio,1.000000,1000.00,1000.00,16\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    data = json.loads(result.model_dump_json())
    iva_str = data["registros"][0]["iva_estimado"]
    assert Decimal(iva_str) == Decimal("16000"), (
        f"Con tasa=16, iva_estimado debe ser 16000, no {iva_str}. "
        "Si da 160, el implementador está normalizando la tasa (bug o feature no especificada)."
    )


# ---------------------------------------------------------------------------
# Adversarial: archivo con columna tasa pero tasa ausente en todas las filas
# ---------------------------------------------------------------------------


def test_columna_tasa_presente_filas_sin_tasa(tmp_path: Path) -> None:
    """Adversarial: columna 'tasa' presente pero todas las filas la tienen vacía → iva_estimado=null todas."""
    csv = (
        "clave_prod_serv,descripcion,cantidad,valor_unitario,importe,tasa\n"
        "84111506,Servicio A,1.000000,10000.00,10000.00,\n"
        "84111507,Servicio B,1.000000,2000.00,2000.00,\n"
    )
    ruta = _csv_to_path(csv, tmp_path)
    result = parsear_tabla(ruta)
    # La columna tasa existe, así que total_iva_estimado debe existir (=0)
    assert result.total_iva_estimado is not None
    for reg in result.registros:
        assert reg.iva_estimado is None

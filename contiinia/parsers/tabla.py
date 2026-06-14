"""Parser de tablas de conceptos CSV/XLSX — CA-TAB-01..09."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

from contiinia.errors import (
    ArchivoNoEncontradoError,
    FormatoNoSoportadoError,
)
from contiinia.models.tabla import TablaResult, TablaRow

# ---------------------------------------------------------------------------
# Mapeo alias → columna canónica
# ---------------------------------------------------------------------------

_ALIAS_MAP: dict[str, str] = {}

_ALIASES: dict[str, list[str]] = {
    "clave_prod_serv": ["clave_prod_serv", "clave", "claveprodsrv", "clave_producto", "clave_sat"],
    "descripcion": ["descripcion", "descripción", "desc", "concepto", "descripcion_concepto"],
    "cantidad": ["cantidad", "qty", "cant", "unidades"],
    "valor_unitario": [
        "valor_unitario",
        "precio",
        "precio_unitario",
        "valor",
        "total_concepto",  # se incluye por robustez
    ],
    "importe": ["importe", "total", "monto", "subtotal", "total_concepto"],
    "impuesto": ["impuesto", "iva", "imptos"],
    "tasa": ["tasa", "tasa_iva", "porcentaje"],
}

# Construir diccionario inverso alias → canónico (en minúsculas)
for _canon, _alias_list in _ALIASES.items():
    for _alias in _alias_list:
        _ALIAS_MAP[_alias.lower()] = _canon


def _to_decimal(value: Any) -> Decimal | None:
    """Convierte un valor a Decimal; retorna None si no es posible."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def _map_columns(df: pd.DataFrame) -> tuple[dict[str, str], list[str]]:
    """
    Retorna:
      - col_map: {columna_original → nombre_canónico}  solo para columnas mapeadas
      - unmapped: columnas originales sin mapear
    """
    col_map: dict[str, str] = {}
    unmapped: list[str] = []
    seen_canonicals: set[str] = set()

    for col in df.columns:
        normalized = col.strip().lower()
        canonical = _ALIAS_MAP.get(normalized)
        if canonical and canonical not in seen_canonicals:
            col_map[col] = canonical
            seen_canonicals.add(canonical)
        else:
            unmapped.append(col)

    return col_map, unmapped


def _detect_csv_separator(ruta: Path) -> str:
    """Detecta si el CSV usa coma o punto y coma como separador."""
    try:
        first_line = ruta.read_text(encoding="utf-8").splitlines()[0]
    except UnicodeDecodeError:
        first_line = ruta.read_text(encoding="latin-1").splitlines()[0]

    semicolons = first_line.count(";")
    commas = first_line.count(",")
    return ";" if semicolons > commas else ","


def _load_dataframe(ruta: Path) -> pd.DataFrame:
    """Carga el DataFrame desde CSV o XLSX según la extensión."""
    ext = ruta.suffix.lower()

    if ext == ".csv":
        sep = _detect_csv_separator(ruta)
        try:
            return pd.read_csv(ruta, sep=sep, encoding="utf-8", dtype=str, keep_default_na=False)
        except UnicodeDecodeError:
            return pd.read_csv(ruta, sep=sep, encoding="latin-1", dtype=str, keep_default_na=False)
    elif ext in {".xlsx", ".xls"}:
        return pd.read_excel(ruta, dtype=str, keep_default_na=False)
    else:
        raise FormatoNoSoportadoError(
            f"Extensión '{ext}' no soportada. Use .csv o .xlsx.",
            archivo=str(ruta),
        )


def parsear_tabla(ruta: Path) -> TablaResult:
    """
    Parsea un archivo CSV o XLSX con una tabla de conceptos.

    Returns:
        TablaResult con los registros normalizados.

    Raises:
        ArchivoNoEncontradoError: si el archivo no existe (exit 3).
        FormatoNoSoportadoError: si la extensión no es .csv/.xlsx (exit 1).
    """
    if not ruta.exists():
        raise ArchivoNoEncontradoError(
            f"Archivo no encontrado: {ruta}",
            archivo=str(ruta),
        )

    df = _load_dataframe(ruta)

    # Eliminar filas completamente vacías
    df = df.replace("", None)
    df = df.dropna(how="all")

    # Mapear columnas
    col_map, unmapped = _map_columns(df)
    columnas_detectadas = list(col_map.values())

    registros: list[TablaRow] = []

    for _, row in df.iterrows():
        # Columnas canónicas
        canonical_vals: dict[str, Any] = {}
        for orig_col, canon in col_map.items():
            val = row.get(orig_col)
            if val == "" or (isinstance(val, float) and pd.isna(val)):
                val = None
            canonical_vals[canon] = val

        # Extras
        extras: dict[str, Any] = {}
        for col in unmapped:
            val = row.get(col)
            if val == "" or (isinstance(val, float) and pd.isna(val)):
                val = None
            extras[col] = val

        # Convertir decimales
        cantidad = _to_decimal(canonical_vals.get("cantidad"))
        valor_unitario = _to_decimal(canonical_vals.get("valor_unitario"))
        importe = _to_decimal(canonical_vals.get("importe"))

        registro = TablaRow(
            clave_prod_serv=canonical_vals.get("clave_prod_serv"),
            descripcion=canonical_vals.get("descripcion"),
            cantidad=cantidad,
            valor_unitario=valor_unitario,
            importe=importe,
            impuesto=canonical_vals.get("impuesto"),
            tasa=canonical_vals.get("tasa"),
            extras=extras,
        )
        registros.append(registro)

    return TablaResult(
        archivo=str(ruta.resolve()),
        filas=len(registros),
        columnas_detectadas=columnas_detectadas,
        registros=registros,
    )

"""Parser de tablas de conceptos CSV/XLSX — CA-TAB-01..09."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

import pandas as pd

from contiinia.errors import (
    ArchivoNoEncontradoError,
    ArchivoSinDatosError,
    ColumnaRequeridaAusenteError,
    FormatoNoSoportadoError,
    ValorNoNumericoError,
)
from contiinia.models.tabla import (
    AdvertenciaImporteInconsistente,
    AdvertenciaTasaNoNumerica,
    TablaResult,
    TablaRow,
)

# ---------------------------------------------------------------------------
# Columnas requeridas según spec 4.5
# ---------------------------------------------------------------------------

_COLUMNAS_REQUERIDAS = frozenset({"clave_prod_serv", "descripcion", "cantidad", "valor_unitario", "importe"})

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


def _is_blank(value: Any) -> bool:
    """Detecta celdas vacías/NaN sin usar float como tipo de dato."""
    if value is None:
        return True
    s = str(value).strip()
    return s == "" or s.lower() in ("nan", "none", "null")


def _to_decimal(value: Any) -> Decimal | None:
    """Convierte un valor a Decimal; retorna None si no es posible."""
    if _is_blank(value):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def _to_decimal_or_error(
    canonical_vals: dict[str, Any],
    field: str,
    fila: int,
    archivo: str,
) -> Decimal | None:
    """Convierte una columna canónica a Decimal; lanza ValorNoNumericoError si no es posible."""
    raw = canonical_vals.get(field)
    if raw is None:
        return None
    result = _to_decimal(raw)
    if result is None:
        raise ValorNoNumericoError(
            f"Valor no numérico en columna '{field}', fila {fila}: {raw!r}",
            archivo=archivo,
        )
    return result


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


def _load_dataframe(ruta: Path) -> tuple[pd.DataFrame, str, list[str | dict[str, Any]]]:
    """Carga el DataFrame desde CSV, XLSX, XLS u ODS. Retorna (df, formato, advertencias).

    QA-TAB-01: para formatos multi-hoja procesa siempre la primera hoja y emite advertencia.
    """
    ext = ruta.suffix.lower()
    advertencias: list[str | dict[str, Any]] = []

    if ext == ".csv":
        sep = _detect_csv_separator(ruta)
        try:
            df = pd.read_csv(ruta, sep=sep, encoding="utf-8", dtype=str, keep_default_na=False)
        except UnicodeDecodeError:
            df = pd.read_csv(ruta, sep=sep, encoding="latin-1", dtype=str, keep_default_na=False)
        return df, "csv", advertencias

    elif ext == ".xlsx":
        xf = pd.ExcelFile(ruta)
        if len(xf.sheet_names) > 1:
            advertencias.append(
                f"El archivo contiene {len(xf.sheet_names)} hojas "
                f"({', '.join(str(s) for s in xf.sheet_names)}); "
                f"se procesó únicamente la primera hoja: '{xf.sheet_names[0]}'."
            )
        df = cast(pd.DataFrame, xf.parse(xf.sheet_names[0], dtype=str, keep_default_na=False))
        return df, "xlsx", advertencias

    elif ext == ".xls":
        xf = pd.ExcelFile(ruta, engine="xlrd")
        if len(xf.sheet_names) > 1:
            advertencias.append(
                f"El archivo contiene {len(xf.sheet_names)} hojas "
                f"({', '.join(str(s) for s in xf.sheet_names)}); "
                f"se procesó únicamente la primera hoja: '{xf.sheet_names[0]}'."
            )
        df = cast(pd.DataFrame, xf.parse(xf.sheet_names[0], dtype=str, keep_default_na=False))
        return df, "xls", advertencias

    elif ext == ".ods":
        xf = pd.ExcelFile(ruta, engine="odf")
        if len(xf.sheet_names) > 1:
            advertencias.append(
                f"El archivo contiene {len(xf.sheet_names)} hojas "
                f"({', '.join(str(s) for s in xf.sheet_names)}); "
                f"se procesó únicamente la primera hoja: '{xf.sheet_names[0]}'."
            )
        df = cast(pd.DataFrame, xf.parse(xf.sheet_names[0], dtype=str, keep_default_na=False))
        return df, "ods", advertencias

    else:
        raise FormatoNoSoportadoError(
            f"Extensión '{ext}' no soportada. Use .csv, .xlsx, .xls u .ods.",
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
        ArchivoSinDatosError: si el archivo está vacío o sin filas de datos (exit 1).
        ColumnaRequeridaAusenteError: si falta una columna requerida (exit 1).
        ValorNoNumericoError: si un campo monetario tiene valor no numérico (exit 1).
    """
    if not ruta.exists():
        raise ArchivoNoEncontradoError(
            f"Archivo no encontrado: {ruta}",
            archivo=str(ruta),
        )

    df, formato, advertencias_carga = _load_dataframe(ruta)

    # Eliminar filas completamente vacías
    df = df.replace("", None)
    df = df.dropna(how="all")

    # Detectar archivo sin datos
    if len(df) == 0:
        raise ArchivoSinDatosError(
            f"El archivo no contiene filas de datos: {ruta}",
            archivo=str(ruta),
        )

    # Mapear columnas
    col_map, unmapped = _map_columns(df)
    columnas_detectadas = list(col_map.values())

    # Verificar columnas requeridas
    columnas_encontradas = set(col_map.values())
    for col_requerida in sorted(_COLUMNAS_REQUERIDAS):
        if col_requerida not in columnas_encontradas:
            raise ColumnaRequeridaAusenteError(
                f"Columna requerida no encontrada: '{col_requerida}'",
                archivo=str(ruta),
            )

    registros: list[TablaRow] = []

    tasa_presente = "tasa" in columnas_detectadas
    total_iva: Decimal | None = Decimal("0") if tasa_presente else None

    for idx, row in df.iterrows():
        fila = int(idx) + 2  # encabezado es fila 1, primer dato es fila 2

        # Columnas canónicas
        canonical_vals: dict[str, Any] = {}
        for orig_col, canon in col_map.items():
            val = row.get(orig_col)
            if _is_blank(val):
                val = None
            canonical_vals[canon] = val

        # Extras
        columnas_extra: dict[str, Any] = {}
        for col in unmapped:
            val = row.get(col)
            if _is_blank(val):
                val = None
            columnas_extra[col] = val

        # Convertir decimales — valor no numérico es error fatal
        archivo_str = str(ruta)
        cantidad = _to_decimal_or_error(canonical_vals, "cantidad", fila, archivo_str)
        valor_unitario = _to_decimal_or_error(canonical_vals, "valor_unitario", fila, archivo_str)
        importe = _to_decimal_or_error(canonical_vals, "importe", fila, archivo_str)

        # Feature 3: IVA estimado por fila
        tasa_raw = canonical_vals.get("tasa") if tasa_presente else None
        iva_estimado: Decimal | None = None
        if tasa_presente and tasa_raw is not None:
            tasa_decimal = _to_decimal(tasa_raw)
            if tasa_decimal is None:
                advertencias_carga.append(AdvertenciaTasaNoNumerica(
                    fila=fila,
                    valor_encontrado=str(tasa_raw),
                ))
            elif importe is not None:
                iva_estimado = importe * tasa_decimal

        registro = TablaRow(
            fila=fila,
            clave_prod_serv=canonical_vals.get("clave_prod_serv"),
            descripcion=canonical_vals.get("descripcion"),
            cantidad=cantidad,
            valor_unitario=valor_unitario,
            importe=importe,
            impuesto=canonical_vals.get("impuesto"),
            tasa=tasa_raw if tasa_presente else None,
            iva_estimado=iva_estimado,
            columnas_extra=columnas_extra,
        )
        registros.append(registro)

        if iva_estimado is not None and total_iva is not None:
            total_iva += iva_estimado

    # Feature 2: validación cruzada de importes
    for registro in registros:
        if (
            registro.cantidad is not None
            and registro.valor_unitario is not None
            and registro.importe is not None
        ):
            esperado = registro.cantidad * registro.valor_unitario
            diferencia = abs(registro.importe - esperado)
            if diferencia > Decimal("0.01"):
                advertencias_carga.append(AdvertenciaImporteInconsistente(
                    fila=registro.fila,
                    importe_declarado=str(registro.importe),
                    importe_calculado=f"{esperado:.2f}",
                    diferencia=f"{diferencia:.2f}",
                ))

    return TablaResult(
        archivo=str(ruta.resolve()),
        formato=formato,
        total_registros=len(registros),
        columnas_detectadas=columnas_detectadas,
        registros=registros,
        total_iva_estimado=total_iva,
        advertencias=advertencias_carga,
    )

"""Parser de lote y detector de duplicados — Hito 4.6."""

from pathlib import Path

from contiinia.errors import (
    ContiiniaError,
    DirectorioNoEncontradoError,
    ExitCode,
    RutaNoEsDirectorioError,
    UnsupportedVersionError,
)
from contiinia.models.lote import (
    DuplicadoAdvertencia,
    DuplicadoItem,
    DuplicadosResult,
    LoteErrorItem,
    LoteResult,
    LoteResultado,
)
from contiinia.parsers.xml import parsear_xml


def parsear_lote(directorio: Path, recursivo: bool = False) -> LoteResult:
    """Parsea todos los XML en el directorio. Tolera errores individuales sin abortar."""
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

    resultados: list[LoteResultado] = []
    for archivo in archivos:
        ruta_str = str(archivo)
        try:
            cfdi = parsear_xml(archivo)
            resultados.append(
                LoteResultado(
                    archivo=ruta_str,
                    estado="ok",
                    datos=cfdi,
                )
            )
        except ContiiniaError as exc:
            resultados.append(
                LoteResultado(
                    archivo=ruta_str,
                    estado="error",
                    error=LoteErrorItem(
                        error=exc.error_type,
                        archivo=exc.archivo or ruta_str,
                        detalle=exc.detalle,
                    ),
                )
            )
        except Exception as exc:
            resultados.append(
                LoteResultado(
                    archivo=ruta_str,
                    estado="error",
                    error=LoteErrorItem(
                        error="error_inesperado",
                        archivo=ruta_str,
                        detalle=str(exc),
                    ),
                )
            )

    exitosos = sum(1 for r in resultados if r.estado == "ok")
    return LoteResult(
        directorio=str(directorio),
        recursivo=recursivo,
        total_archivos=len(resultados),
        exitosos=exitosos,
        errores=len(resultados) - exitosos,
        resultados=resultados,
    )


def detectar_duplicados(directorio: Path, recursivo: bool = False) -> DuplicadosResult:
    """Detecta UUIDs duplicados en un directorio de CFDIs."""
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

    uuid_map: dict[str, list[str]] = {}
    advertencias: list[DuplicadoAdvertencia] = []

    for archivo in archivos:
        ruta_str = str(archivo)
        try:
            cfdi = parsear_xml(archivo)
            if cfdi.uuid:
                uuid = cfdi.uuid  # already uppercase from parser
                if uuid not in uuid_map:
                    uuid_map[uuid] = []
                uuid_map[uuid].append(ruta_str)
            else:
                advertencias.append(
                    DuplicadoAdvertencia(
                        archivo=ruta_str,
                        motivo="sin_timbre",
                    )
                )
        except ContiiniaError as exc:
            advertencias.append(
                DuplicadoAdvertencia(
                    archivo=ruta_str,
                    motivo=exc.error_type,
                )
            )
        except Exception as exc:
            advertencias.append(
                DuplicadoAdvertencia(
                    archivo=ruta_str,
                    motivo="error_inesperado",
                )
            )

    duplicados = [
        DuplicadoItem(uuid=uuid, ocurrencias=len(archivos_list), archivos=archivos_list)
        for uuid, archivos_list in uuid_map.items()
        if len(archivos_list) > 1
    ]

    return DuplicadosResult(
        directorio=str(directorio),
        recursivo=recursivo,
        total_archivos_procesados=len(archivos),
        total_duplicados=len(duplicados),
        duplicados=duplicados,
        advertencias=advertencias,
    )

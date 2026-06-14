"""Jerarquía de errores, exit codes y emit_error para contiinia."""

import json
import sys
from enum import IntEnum
from typing import NoReturn


class ExitCode(IntEnum):
    SUCCESS = 0
    BUSINESS = 1
    UNSUPPORTED_VERSION = 2
    SYSTEM = 3


class ContiiniaError(Exception):
    """Base. Todos los errores del CLI heredan de aquí."""

    exit_code: int = ExitCode.BUSINESS
    error_type: str = "error_interno"

    def __init__(self, detalle: str, archivo: str | None = None) -> None:
        super().__init__(detalle)
        self.detalle = detalle
        self.archivo = archivo


class BusinessError(ContiiniaError):
    """Exit 1: RFC inválido, campo faltante, regla fiscal violada."""

    exit_code = ExitCode.BUSINESS


class UnsupportedVersionError(ContiiniaError):
    """Exit 2: CFDI 3.3 o namespace desconocido."""

    exit_code = ExitCode.UNSUPPORTED_VERSION
    error_type = "version_no_soportada"


class SystemError(ContiiniaError):  # noqa: A001
    """Exit 3: archivo no encontrado, permisos, corrupción irrecuperable."""

    exit_code = ExitCode.SYSTEM


# Subclases de BusinessError (exit 1)
class CampoRequeridoAusenteError(BusinessError):
    error_type = "campo_requerido_ausente"


class TipoComprobanteInvalidoError(BusinessError):
    error_type = "tipo_comprobante_invalido"


class FormatoNoSoportadoError(BusinessError):
    error_type = "formato_no_soportado"


class ColumnaRequeridaAusenteError(BusinessError):
    error_type = "columna_requerida_ausente"


class ArchivoSinDatosError(BusinessError):
    error_type = "archivo_sin_datos"


class ValorNoNumericoError(BusinessError):
    error_type = "valor_no_numerico"


# Subclases de SystemError (exit 3)
class ArchivoNoEncontradoError(SystemError):
    error_type = "archivo_no_encontrado"


class XmlMalformadoError(SystemError):
    error_type = "xml_malformado"


class ArchivoVacioError(SystemError):
    error_type = "archivo_vacio"


class EncodingInvalidoError(SystemError):
    error_type = "encoding_invalido"


class DirectorioNoEncontradoError(SystemError):
    error_type = "directorio_no_encontrado"


class RutaNoEsDirectorioError(SystemError):
    error_type = "ruta_no_es_directorio"


class PermisoDenegadoError(SystemError):
    error_type = "permiso_denegado"


class ArchivoCorrumpidoError(SystemError):
    error_type = "archivo_corrupto"


class ErrorEscrituraError(SystemError):
    error_type = "error_escritura"


def emit_error(exc: ContiiniaError) -> NoReturn:
    """Emite JSON al stderr y sale con el exit code correcto."""
    payload = {
        "error": exc.error_type,
        "archivo": exc.archivo,
        "detalle": exc.detalle,
    }
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)
    sys.exit(exc.exit_code)

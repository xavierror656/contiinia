"""Modelo VersionInfo — salida de `contiinia version`."""

from pydantic import BaseModel, ConfigDict


class VersionInfo(BaseModel):
    """Información de versión del CLI."""

    model_config = ConfigDict(populate_by_name=True)

    cli: str = "contiinia"
    version: str = "1.2.0"
    cfdi_soportados: list[str] = ["4.0"]
    spec_version: str = "1.1"

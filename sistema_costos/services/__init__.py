"""Servicios de transformación y exportación."""

__all__ = ["ETLService", "ExcelExporter"]


def __getattr__(name: str):
    if name == "ETLService":
        from .etl_service import ETLService
        return ETLService

    if name == "ExcelExporter":
        from .exporter import ExcelExporter
        return ExcelExporter

    raise AttributeError(f"No existe el servicio: {name}")
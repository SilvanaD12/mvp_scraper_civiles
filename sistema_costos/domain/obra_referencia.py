from dataclasses import dataclass


@dataclass(frozen=True)
class ObraReferencia:
    fuente: str
    codigo_fuente: str
    nombre: str
    url: str
    extraido_en: str
    cui: str | None = None
    entidad: str | None = None
    ubicacion: str | None = None
    monto_aprobacion_texto: str | None = None
    fecha_aprobacion_texto: str | None = None
"""Modelo de una partida candidata encontrada en un documento."""

from dataclasses import dataclass
from enum import Enum


class EstadoRevision(str, Enum):
    PENDIENTE = "pendiente"
    REVISADO = "revisado"
    RECHAZADO = "rechazado"


@dataclass(frozen=True, slots=True)
class PartidaCandidata:
    documento_id: str
    pagina: int
    descripcion: str
    texto_evidencia: str

    unidad: str | None = None
    cantidad_texto: str | None = None
    precio_unitario_texto: str | None = None
    moneda: str | None = None

    def __post_init__(self) -> None:
        if not self.documento_id.strip():
            raise ValueError(
                "Debe indicarse el documento de origen."
            )

        if (
            not isinstance(self.pagina, int)
            or isinstance(self.pagina, bool)
            or self.pagina < 1
        ):
            raise ValueError(
                "La página debe ser un entero mayor que cero."
            )

        if not self.descripcion.strip():
            raise ValueError(
                "La descripción no puede estar vacía."
            )

        if not self.texto_evidencia.strip():
            raise ValueError(
                "Debe conservarse el texto que respalda el hallazgo."
            )
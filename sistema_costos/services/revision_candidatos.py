"""Consulta de hallazgos e incorporación de los datos seleccionados."""

from pathlib import Path
from dataclasses import dataclass

from sistema_costos.database.candidatos_repository import (
    CandidatosRepository,
)
from sistema_costos.database.partidas_seleccionadas_repository import (
    PartidasSeleccionadasRepository,
)


@dataclass(frozen=True)
class FuentePartida:
    documento: str | None
    pagina: int | None
    ruta_local: Path | None
    estado: str
    aviso: str = ""

    @property
    def disponible(self) -> bool:
        return self.estado == "disponible"


class RevisionCandidatosService:
    def __init__(
        self,
        repositorio: CandidatosRepository,
        seleccionados: PartidasSeleccionadasRepository,
    ) -> None:
        self._repositorio = repositorio
        self._seleccionados = seleccionados

    def listar(self, guardadas: bool = False) -> list[dict]:
        return self._seleccionados.listar(
            guardadas=guardadas
        )

    def guardar_seleccion(
        self,
        candidato_ids: list[str],
    ) -> int:
        return self._seleccionados.guardar(candidato_ids)

    def obtener(self, candidato_id: str) -> dict:
        for candidato in self._repositorio.listar():
            if candidato["id"] == candidato_id:
                return candidato

        raise ValueError("El dato extraído no existe.")

    def obtener_ruta_pdf(
        self,
        candidato_id: str,
    ) -> Path:
        fuente = self.describir_fuente(self.obtener(candidato_id))
        if fuente.disponible and fuente.ruta_local is not None:
            return fuente.ruta_local
        if fuente.estado == "no_disponible":
            raise FileNotFoundError(fuente.aviso)
        raise ValueError(fuente.aviso)

    @staticmethod
    def describir_fuente(fila: dict) -> FuentePartida:
        documento, pagina = fila.get("documento_nombre"), fila.get("pagina")
        texto = (fila.get("ruta_local") or "").strip()
        if not texto:
            return FuentePartida(documento, pagina, None, "sin_ruta",
                                 "El documento no tiene una ruta local registrada.")
        ruta = Path(texto)
        if ruta.suffix.lower() != ".pdf":
            return FuentePartida(documento, pagina, ruta, "no_es_pdf",
                                 "El documento registrado no es un archivo PDF.")
        try:
            ruta = ruta.expanduser()
            if ruta.is_file():
                return FuentePartida(documento, pagina, ruta.resolve(), "disponible")
        except (OSError, RuntimeError, ValueError):
            pass
        return FuentePartida(documento, pagina, ruta, "no_disponible",
                             "El PDF ya no está disponible en la ruta registrada. "
                             "Vuelve a descargarlo o cárgalo nuevamente.")

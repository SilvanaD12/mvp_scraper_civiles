"""Consulta de hallazgos e incorporación de los datos seleccionados."""

from pathlib import Path

from sistema_costos.database.candidatos_repository import (
    CandidatosRepository,
)
from sistema_costos.database.partidas_seleccionadas_repository import (
    PartidasSeleccionadasRepository,
)


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
        candidato = self.obtener(candidato_id)
        ruta_texto = candidato["ruta_local"]

        if not ruta_texto or not ruta_texto.strip():
            raise ValueError(
                "El documento no tiene una ruta local registrada."
            )

        ruta = Path(ruta_texto).expanduser()

        if ruta.suffix.lower() != ".pdf":
            raise ValueError(
                "El documento registrado no es un archivo PDF."
            )

        if not ruta.is_file():
            raise FileNotFoundError(
                f"No se encontró el PDF en la ruta registrada: {ruta}"
            )

        return ruta.resolve()
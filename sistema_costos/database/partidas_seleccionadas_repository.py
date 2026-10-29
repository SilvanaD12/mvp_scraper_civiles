"""Registro de los hallazgos que el usuario elige incorporar."""

from datetime import datetime, timezone
from pathlib import Path

from .connection import DatabaseConnection


class PartidasSeleccionadasRepository:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

        with DatabaseConnection(self.path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS partidas_seleccionadas (
                    candidato_id TEXT PRIMARY KEY
                        REFERENCES partidas_candidatas(id),
                    guardado_en TEXT NOT NULL
                )
            """)

    def guardar(self, candidato_ids: list[str]) -> int:
        """Guarda la selección completa y devuelve cuántos son nuevos."""
        if not isinstance(candidato_ids, list):
            raise ValueError(
                "La selección debe ser una lista de identificadores."
            )

        if not candidato_ids:
            raise ValueError(
                "Selecciona al menos un dato para guardar."
            )

        if any(
            not isinstance(valor, str) or not valor.strip()
            for valor in candidato_ids
        ):
            raise ValueError(
                "La selección contiene identificadores inválidos."
            )

        identificadores = list(dict.fromkeys(candidato_ids))
        fecha = datetime.now(timezone.utc).isoformat()
        nuevos = 0

        with DatabaseConnection(self.path) as db:
            db.execute("BEGIN IMMEDIATE")

            for candidato_id in identificadores:
                existente = db.fetch_one(
                    """
                    SELECT id
                    FROM partidas_candidatas
                    WHERE id = ?
                    """,
                    (candidato_id,),
                )

                if existente is None:
                    raise ValueError(
                        "Uno de los datos seleccionados no existe. "
                        "No se guardó la selección."
                    )

                cursor = db.execute(
                    """
                    INSERT INTO partidas_seleccionadas (
                        candidato_id,
                        guardado_en
                    )
                    VALUES (?, ?)
                    ON CONFLICT(candidato_id) DO NOTHING
                    """,
                    (candidato_id, fecha),
                )

                nuevos += cursor.rowcount

        return nuevos

    def listar(self, guardadas: bool = True) -> list[dict]:
        """Consulta datos incorporados o hallazgos sin incorporar."""
        consulta = """
            SELECT
                c.*,
                d.nombre AS documento_nombre,
                d.ruta_local,
                d.fuente,
                d.obra_clave,
                s.guardado_en
            FROM partidas_candidatas AS c
            JOIN documentos_revision AS d
                ON d.id = c.documento_id
            LEFT JOIN partidas_seleccionadas AS s
                ON s.candidato_id = c.id
        """

        if guardadas:
            consulta += " WHERE s.candidato_id IS NOT NULL"
        else:
            consulta += " WHERE s.candidato_id IS NULL"

        consulta += " ORDER BY c.creado_en DESC, c.id"

        with DatabaseConnection(self.path) as db:
            return [
                dict(fila)
                for fila in db.fetch_all(consulta)
            ]
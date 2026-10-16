from dataclasses import asdict
from pathlib import Path

from ..domain.obra_referencia import ObraReferencia
from .connection import DatabaseConnection


class ObrasRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def inicializar(self) -> None:
        with DatabaseConnection(self.database_path) as database:
            database.execute("""
                CREATE TABLE IF NOT EXISTS obras_referencias (
                    fuente TEXT NOT NULL,
                    codigo_fuente TEXT NOT NULL,
                    nombre TEXT NOT NULL,
                    url TEXT NOT NULL,
                    extraido_en TEXT NOT NULL,
                    cui TEXT,
                    entidad TEXT,
                    ubicacion TEXT,
                    monto_aprobacion_texto TEXT,
                    fecha_aprobacion_texto TEXT,
                    PRIMARY KEY (fuente, codigo_fuente)
                )
            """)

    def guardar(self, obra: ObraReferencia) -> None:
        datos = asdict(obra)

        with DatabaseConnection(self.database_path) as database:
            database.execute(
                """
                INSERT INTO obras_referencias (
                    fuente, codigo_fuente, nombre, url,
                    extraido_en, cui, entidad, ubicacion,
                    monto_aprobacion_texto, fecha_aprobacion_texto
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (fuente, codigo_fuente)
                DO UPDATE SET
                    nombre = excluded.nombre,
                    url = excluded.url,
                    extraido_en = excluded.extraido_en,
                    cui = excluded.cui,
                    entidad = excluded.entidad,
                    ubicacion = excluded.ubicacion,
                    monto_aprobacion_texto =
                        excluded.monto_aprobacion_texto,
                    fecha_aprobacion_texto =
                        excluded.fecha_aprobacion_texto
                """,
                (
                    datos["fuente"],
                    datos["codigo_fuente"],
                    datos["nombre"],
                    datos["url"],
                    datos["extraido_en"],
                    datos["cui"],
                    datos["entidad"],
                    datos["ubicacion"],
                    datos["monto_aprobacion_texto"],
                    datos["fecha_aprobacion_texto"],
                ),
            )

    def obtener(
        self,
        fuente: str,
        codigo: str,
    ) -> ObraReferencia | None:
        with DatabaseConnection(self.database_path) as database:
            fila = database.fetch_one(
                """
                SELECT * FROM obras_referencias
                WHERE fuente = ? AND codigo_fuente = ?
                """,
                (fuente, codigo),
            )

        return ObraReferencia(**dict(fila)) if fila else None

    def contar(self) -> int:
        with DatabaseConnection(self.database_path) as database:
            fila = database.fetch_one(
                "SELECT COUNT(*) AS total FROM obras_referencias"
            )

        return int(fila["total"])
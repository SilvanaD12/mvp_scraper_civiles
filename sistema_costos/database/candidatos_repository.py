"""Persistencia de documentos, candidatos e historial de revisión."""

import hashlib
import json

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .connection import DatabaseConnection
from ..domain.partida_candidata import (
    EstadoRevision,
    PartidaCandidata,
)


class CandidatosRepository:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

        with DatabaseConnection(self.path) as db:
            db.executescript("""
                BEGIN IMMEDIATE;

                CREATE TABLE IF NOT EXISTS revision_migrations (
                    version INTEGER PRIMARY KEY,
                    aplicada_en TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS documentos_revision (
                    id TEXT PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    ruta_local TEXT NOT NULL,
                    fuente TEXT NOT NULL,
                    obra_clave TEXT
                );

                CREATE TABLE IF NOT EXISTS partidas_candidatas (
                    id TEXT PRIMARY KEY,
                    documento_id TEXT NOT NULL
                        REFERENCES documentos_revision(id),
                    pagina INTEGER NOT NULL CHECK (pagina >= 1),
                    descripcion TEXT NOT NULL,
                    texto_evidencia TEXT NOT NULL,
                    unidad TEXT,
                    cantidad_texto TEXT,
                    precio_unitario_texto TEXT,
                    moneda TEXT,
                    estado TEXT NOT NULL DEFAULT 'pendiente'
                        CHECK (
                            estado IN (
                                'pendiente',
                                'revisado',
                                'rechazado'
                            )
                        ),
                    creado_en TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS revisiones_candidatas (
                    id INTEGER PRIMARY KEY,
                    candidato_id TEXT NOT NULL
                        REFERENCES partidas_candidatas(id),
                    estado_anterior TEXT NOT NULL,
                    estado_nuevo TEXT NOT NULL
                        CHECK (
                            estado_nuevo IN (
                                'pendiente',
                                'revisado',
                                'rechazado'
                            )
                        ),
                    responsable TEXT NOT NULL,
                    observacion TEXT NOT NULL,
                    revisado_en TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_candidatas_documento
                    ON partidas_candidatas(documento_id, pagina);

                INSERT OR IGNORE INTO revision_migrations
                    (version, aplicada_en)
                VALUES (
                    1,
                    strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                );

                COMMIT;
            """)

            # Agregar los campos nuevos sin eliminar datos existentes.
            db.execute("BEGIN IMMEDIATE")

            columnas = {
                fila["name"]
                for fila in db.fetch_all(
                    "PRAGMA table_info(partidas_candidatas)"
                )
            }

            for nombre, tipo in (
                ("obra", "TEXT"),
                ("anio", "INTEGER"),
                ("lugar", "TEXT"),
                ("monto_texto", "TEXT"),
                ("tipo_monto", "TEXT"),
            ):
                if nombre not in columnas:
                    db.execute(
                        f"ALTER TABLE partidas_candidatas "
                        f"ADD COLUMN {nombre} {tipo}"
                    )

            db.execute(
                "INSERT OR IGNORE INTO revision_migrations "
                "(version, aplicada_en) "
                "VALUES (2, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"
            )

    def registrar_documento(
        self,
        documento_id: str,
        nombre: str,
        ruta_local: str,
        fuente: str,
        obra_clave: str | None = None,
    ) -> None:
        valores = (
            documento_id,
            nombre,
            ruta_local,
            fuente,
            obra_clave,
        )

        if any(
            not isinstance(valor, str) or not valor.strip()
            for valor in valores[:4]
        ):
            raise ValueError(
                "Identificador, nombre, ruta y fuente "
                "son obligatorios."
            )

        with DatabaseConnection(self.path) as db:
            existente = db.fetch_one(
                """
                SELECT id, nombre, ruta_local, fuente, obra_clave
                FROM documentos_revision
                WHERE id = ?
                """,
                (documento_id,),
            )

            if existente is not None:
                if tuple(existente) != valores:
                    raise ValueError(
                        "El identificador ya corresponde "
                        "a otro registro documental."
                    )
                return

            db.execute(
                """
                INSERT INTO documentos_revision (
                    id,
                    nombre,
                    ruta_local,
                    fuente,
                    obra_clave
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                valores,
            )

    def guardar(self, candidato: PartidaCandidata) -> str:
        datos = asdict(candidato)

        nuevos = (
            "obra",
            "anio",
            "lugar",
            "monto_texto",
            "tipo_monto",
        )

        # Mantener los identificadores de las partidas existentes.
        identidad = {
            campo: valor
            for campo, valor in datos.items()
            if campo not in nuevos
        }

        # Diferenciar montos generales sin precio unitario.
        if candidato.precio_unitario_texto is None:
            for campo in ("monto_texto", "tipo_monto"):
                if datos[campo] is not None:
                    identidad[campo] = datos[campo]

        contenido = json.dumps(
            identidad,
            ensure_ascii=False,
            sort_keys=True,
        )

        identificador = hashlib.sha256(
            contenido.encode("utf-8")
        ).hexdigest()

        campos = tuple(datos)
        columnas = ", ".join(campos)
        parametros = ", ".join("?" for _ in campos)

        # Un valor ausente no borra contexto guardado previamente.
        actualizaciones = ", ".join(
            f"{campo} = COALESCE("
            f"excluded.{campo}, partidas_candidatas.{campo})"
            for campo in nuevos
        )

        with DatabaseConnection(self.path) as db:
            db.execute(
                f"INSERT INTO partidas_candidatas "
                f"(id, {columnas}, creado_en) "
                f"VALUES (?, {parametros}, ?) "
                f"ON CONFLICT(id) DO UPDATE SET {actualizaciones}",
                (
                    identificador,
                    *(datos[campo] for campo in campos),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

        return identificador

    def listar(
        self,
        estado: EstadoRevision | None = None,
    ) -> list[dict]:
        consulta = """
            SELECT
                c.*,
                d.nombre AS documento_nombre,
                d.ruta_local,
                d.fuente,
                d.obra_clave
            FROM partidas_candidatas AS c
            JOIN documentos_revision AS d
                ON d.id = c.documento_id
        """

        parametros = ()

        if estado is not None:
            consulta += " WHERE c.estado = ?"
            parametros = (EstadoRevision(estado).value,)

        consulta += " ORDER BY c.creado_en DESC, c.id"

        with DatabaseConnection(self.path) as db:
            return [
                dict(fila)
                for fila in db.fetch_all(consulta, parametros)
            ]

    def revisar(
        self,
        candidato_id: str,
        estado: EstadoRevision,
        responsable: str = "",
        observacion: str = "",
    ) -> None:
        nuevo_estado = EstadoRevision(estado).value

        with DatabaseConnection(self.path) as db:
            db.execute("BEGIN IMMEDIATE")

            fila = db.fetch_one(
                """
                SELECT estado
                FROM partidas_candidatas
                WHERE id = ?
                """,
                (candidato_id,),
            )

            if fila is None:
                raise ValueError(
                    "La partida candidata no existe."
                )

            db.execute(
                """
                INSERT INTO revisiones_candidatas (
                    candidato_id,
                    estado_anterior,
                    estado_nuevo,
                    responsable,
                    observacion,
                    revisado_en
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    candidato_id,
                    fila["estado"],
                    nuevo_estado,
                    responsable.strip(),
                    observacion,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

            db.execute(
                """
                UPDATE partidas_candidatas
                SET estado = ?
                WHERE id = ?
                """,
                (nuevo_estado, candidato_id),
            )
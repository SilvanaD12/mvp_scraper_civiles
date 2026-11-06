"""Pruebas aisladas: no modifican la base real del proyecto."""

import sqlite3
import tempfile
import unittest

from contextlib import closing
from pathlib import Path

from sistema_costos.database.candidatos_repository import (
    CandidatosRepository,
)
from sistema_costos.database.connection import DatabaseError
from sistema_costos.domain.partida_candidata import (
    EstadoRevision,
    PartidaCandidata,
)


class CandidatosTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)

        self.ruta = Path(self.temporal.name) / "prueba.db"
        self.repo = CandidatosRepository(self.ruta)

        self.repo.registrar_documento(
            documento_id="doc-prueba",
            nombre="ficticio.pdf",
            ruta_local=str(
                Path(self.temporal.name) / "ficticio.pdf"
            ),
            fuente="PRUEBA",
        )

        self.candidato = PartidaCandidata(
            documento_id="doc-prueba",
            pagina=2,
            descripcion="Partida ficticia",
            texto_evidencia="Texto ficticio con precio 1.234,56",
            unidad="m2",
            precio_unitario_texto="1.234,56",
        )

    def test_guarda_evidencia_y_precio_original(self) -> None:
        identificador = self.repo.guardar(self.candidato)

        filas = self.repo.listar(EstadoRevision.PENDIENTE)

        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["id"], identificador)
        self.assertEqual(filas[0]["pagina"], 2)
        self.assertEqual(
            filas[0]["texto_evidencia"],
            self.candidato.texto_evidencia,
        )
        self.assertEqual(
            filas[0]["precio_unitario_texto"],
            "1.234,56",
        )
        self.assertIsNone(filas[0]["cantidad_texto"])
        self.assertIsNone(filas[0]["moneda"])

    def test_repetir_guardado_no_duplica_ni_borra_revision(
        self,
    ) -> None:
        identificador = self.repo.guardar(self.candidato)

        self.repo.revisar(
            identificador,
            EstadoRevision.REVISADO,
            "Revisor de prueba",
        )

        repetido = self.repo.guardar(self.candidato)

        self.assertEqual(repetido, identificador)
        self.assertEqual(len(self.repo.listar()), 1)
        self.assertEqual(
            self.repo.listar()[0]["estado"],
            "revisado",
        )
        self.assertEqual(
            self.repo.listar(EstadoRevision.PENDIENTE),
            [],
        )

    def test_rechaza_documento_no_registrado(self) -> None:
        candidato = PartidaCandidata(
            documento_id="inexistente",
            pagina=1,
            descripcion="Prueba",
            texto_evidencia="Evidencia ficticia",
        )

        with self.assertRaises(DatabaseError):
            self.repo.guardar(candidato)

        self.assertEqual(self.repo.listar(), [])

    def test_conserva_historial_de_cambios(self) -> None:
        identificador = self.repo.guardar(self.candidato)

        self.repo.revisar(
            identificador,
            EstadoRevision.REVISADO,
            "Revisor de prueba",
            "Primera revisión",
        )

        self.repo.revisar(
            identificador,
            EstadoRevision.PENDIENTE,
            "Revisor de prueba",
            "Revisar otra vez",
        )

        # closing garantiza que la conexión se cierre.
        with closing(sqlite3.connect(self.ruta)) as conexion:
            filas = conexion.execute(
                """
                SELECT
                    estado_anterior,
                    estado_nuevo,
                    responsable,
                    observacion
                FROM revisiones_candidatas
                ORDER BY id
                """
            ).fetchall()

        self.assertEqual(len(filas), 2)
        self.assertEqual(
            filas[0][:2],
            ("pendiente", "revisado"),
        )
        self.assertEqual(
            filas[1][:2],
            ("revisado", "pendiente"),
        )
        self.assertEqual(
            filas[1][2:],
            ("Revisor de prueba", "Revisar otra vez"),
        )
        self.assertEqual(
            len(self.repo.listar(EstadoRevision.PENDIENTE)),
            1,
        )

    def test_revision_inexistente_no_deja_historial(self) -> None:
        with self.assertRaises(ValueError):
            self.repo.revisar(
                "inexistente",
                EstadoRevision.RECHAZADO,
                "Revisor de prueba",
            )

        with closing(sqlite3.connect(self.ruta)) as conexion:
            cantidad = conexion.execute(
                "SELECT COUNT(*) FROM revisiones_candidatas"
            ).fetchone()[0]

        self.assertEqual(cantidad, 0)

    def test_inicializar_otra_vez_conserva_datos(self) -> None:
        with closing(sqlite3.connect(self.ruta)) as conexion:
            # Este bloque confirma la transacción.
            # El bloque exterior cierra la conexión.
            with conexion:
                conexion.execute(
                    "CREATE TABLE tabla_anterior (dato TEXT)"
                )
                conexion.execute(
                    "INSERT INTO tabla_anterior VALUES (?)",
                    ("conservar",),
                )

        self.repo.guardar(self.candidato)

        # Inicializar de nuevo debe conservar los datos.
        CandidatosRepository(self.ruta)

        with closing(sqlite3.connect(self.ruta)) as conexion:
            dato = conexion.execute(
                "SELECT dato FROM tabla_anterior"
            ).fetchone()[0]

            versiones = conexion.execute(
                """
                SELECT COUNT(*)
                FROM revision_migrations
                WHERE version = 1
                """
            ).fetchone()[0]

        self.assertEqual(dato, "conservar")
        self.assertEqual(versiones, 1)
        self.assertEqual(len(self.repo.listar()), 1)


if __name__ == "__main__":
    unittest.main()
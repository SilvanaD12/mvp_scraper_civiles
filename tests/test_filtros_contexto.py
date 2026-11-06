"""Pruebas de filtros y persistencia del contexto."""

import tempfile
import unittest
from pathlib import Path

from sistema_costos.database.candidatos_repository import (
    CandidatosRepository,
)
from sistema_costos.database.partidas_seleccionadas_repository import (
    PartidasSeleccionadasRepository,
)
from sistema_costos.domain.partida_candidata import PartidaCandidata
from sistema_costos.services.consulta_resultados import ConsultaResultados
from sistema_costos.services.revision_candidatos import (
    RevisionCandidatosService,
)


class FiltrosContextoTests(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)

        self.ruta = Path(temporal.name) / "pruebas.db"
        self.repo = CandidatosRepository(self.ruta)
        self.seleccionados = PartidasSeleccionadasRepository(self.ruta)

        self.repo.registrar_documento(
            "doc",
            "documento.pdf",
            str(Path(temporal.name) / "documento.pdf"),
            "PRUEBA",
            "Referencia anterior",
        )

        self.a = self.repo.guardar(
            PartidaCandidata(
                documento_id="doc",
                pagina=1,
                descripcion="Concreto",
                texto_evidencia="Concreto M3 150.00",
                unidad="M3",
                precio_unitario_texto="150.00",
                obra="Colegio San José",
                anio=2026,
                lugar="Trujillo",
            )
        )

        self.b = self.repo.guardar(
            PartidaCandidata(
                documento_id="doc",
                pagina=2,
                descripcion="Tubería",
                texto_evidencia="Tubería M 20.00",
                unidad="M",
                precio_unitario_texto="20.00",
                obra="Campamento Norte",
                anio=2025,
                lugar="Piura",
            )
        )

        self.sin_contexto = self.repo.guardar(
            PartidaCandidata(
                documento_id="doc",
                pagina=3,
                descripcion="Partida sin contexto",
                texto_evidencia="Evidencia sin año ni lugar",
            )
        )

        servicio = RevisionCandidatosService(
            self.repo,
            self.seleccionados,
        )
        self.consulta = ConsultaResultados(servicio)

    def ids(self, **filtros):
        return {
            fila["id"]
            for fila in self.consulta.actualizar(**filtros)
        }

    def test_filtros_vacios_incluyen_datos_sin_contexto(self):
        self.assertEqual(
            self.ids(),
            {self.a, self.b, self.sin_contexto},
        )

    def test_filtra_obra_sin_acentos(self):
        self.assertEqual(
            self.ids(obra="SAN JOSE"),
            {self.a},
        )

    def test_filtra_anio_exacto(self):
        self.assertEqual(self.ids(anio="2026"), {self.a})
        self.assertEqual(self.ids(anio=2025), {self.b})

    def test_filtra_lugar(self):
        self.assertEqual(
            self.ids(lugar="TRUJILLO"),
            {self.a},
        )

    def test_combina_filtros_y_busqueda(self):
        self.assertEqual(
            self.ids(
                obra="colegio",
                anio="2026",
                lugar="trujillo",
                termino="concreto",
            ),
            {self.a},
        )

        self.assertEqual(
            self.ids(obra="colegio", lugar="piura"),
            set(),
        )

    def test_rechaza_anio_invalido(self):
        for valor in ("26", "202", "20266", "abcd", "20.5"):
            with self.subTest(anio=valor):
                with self.assertRaises(ValueError):
                    self.consulta.actualizar(anio=valor)

    def test_guarda_solo_resultados_filtrados(self):
        self.consulta.actualizar(lugar="piura")
        self.consulta.seleccionar_todos()

        self.assertEqual(self.consulta.guardar(), 1)
        self.assertEqual(
            {fila["id"] for fila in self.seleccionados.listar()},
            {self.b},
        )

        self.assertEqual(
            self.ids(guardadas=True, anio=2025),
            {self.b},
        )

    def test_contexto_persiste_al_reabrir(self):
        reabierto = CandidatosRepository(self.ruta)

        fila = next(
            fila
            for fila in reabierto.listar()
            if fila["id"] == self.a
        )

        self.assertEqual(fila["obra"], "Colegio San José")
        self.assertEqual(fila["anio"], 2026)
        self.assertEqual(fila["lugar"], "Trujillo")

        sin_contexto = next(
            fila
            for fila in reabierto.listar()
            if fila["id"] == self.sin_contexto
        )

        self.assertIsNone(sin_contexto["anio"])
        self.assertIsNone(sin_contexto["lugar"])


if __name__ == "__main__":
    unittest.main()
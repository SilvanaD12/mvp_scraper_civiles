"""Consulta integrada con SQLite temporal; nunca usa datos de la aplicación."""
import tempfile
import unittest
from pathlib import Path

from sistema_costos.database.candidatos_repository import CandidatosRepository
from sistema_costos.database.partidas_seleccionadas_repository import PartidasSeleccionadasRepository
from sistema_costos.domain.partida_candidata import PartidaCandidata
from sistema_costos.services.revision_candidatos import RevisionCandidatosService
from sistema_costos.services.consulta_resultados import ConsultaResultados


class ConsultaResultadosTests(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.ruta = Path(temporal.name) / 'datos.db'
        repo = CandidatosRepository(self.ruta)
        self.seleccionados = PartidasSeleccionadasRepository(self.ruta)
        for doc, fuente, obra in [('a', 'INFOBRAS', 'Lomas de Ilo'),
                                  ('b', 'SEACE', 'Campamento Sur')]:
            repo.registrar_documento(doc, doc + '.pdf', str(Path(temporal.name) / (doc + '.pdf')),
                                     fuente, obra)
        self.a = repo.guardar(PartidaCandidata('a', 2, 'Demolición de sardinel',
            'Evidencia a', unidad='M', precio_unitario_texto='1.234,56', moneda='PEN'))
        self.b = repo.guardar(PartidaCandidata('b', 3, 'Tubería PVC', 'Evidencia b',
            unidad='M', precio_unitario_texto='14.14'))
        self.c = repo.guardar(PartidaCandidata('a', 4, 'Concreto', 'Evidencia c'))
        self.servicio = RevisionCandidatosService(repo, self.seleccionados)
        self.consulta = ConsultaResultados(self.servicio)

    def test_documento_evita_mezclar_resultados(self):
        filas = self.consulta.actualizar(documento_id='a')
        self.assertEqual({f['id'] for f in filas}, {self.a, self.c})
        self.assertEqual(len(self.consulta.actualizar()), 3)

    def test_busca_sin_acentos_por_descripcion_obra_y_fuente(self):
        filas = self.consulta.actualizar(termino='DEMOLICION ilo infobras')
        self.assertEqual([f['id'] for f in filas], [self.a])
        self.assertEqual(self.consulta.actualizar(termino='demolicion seace'), [])

    def test_seleccionar_visibles_solo_guarda_resultados_filtrados(self):
        self.consulta.actualizar(termino='tuberia')
        self.consulta.seleccionar_todos()
        self.assertEqual(self.consulta.guardar(), 1)
        self.assertEqual([f['id'] for f in self.seleccionados.listar()], [self.b])
        self.assertEqual(len(self.seleccionados.listar(guardadas=False)), 2)

    def test_cambio_filtro_limpia_marcas_de_filas_ocultas(self):
        self.consulta.actualizar(documento_id='a')
        self.consulta.seleccionar_todos()
        self.consulta.actualizar(documento_id='b')
        with self.assertRaises(ValueError):
            self.consulta.guardar()
        self.assertEqual(self.seleccionados.listar(), [])

    def test_cancelar_no_guarda_ni_borra_candidatos(self):
        self.consulta.actualizar()
        self.consulta.seleccionar_todos()
        self.consulta.cancelar()
        with self.assertRaises(ValueError):
            self.consulta.guardar()
        self.assertEqual(len(self.seleccionados.listar(guardadas=False)), 3)
        self.assertEqual(self.seleccionados.listar(), [])

    def test_guardadas_son_persistentes_con_precio_y_evidencia_original(self):
        self.consulta.actualizar()
        self.consulta.alternar(self.a)
        self.assertEqual(self.consulta.guardar(), 1)
        reabierto = PartidasSeleccionadasRepository(self.ruta)
        fila = reabierto.listar()[0]
        self.assertEqual(fila['precio_unitario_texto'], '1.234,56')
        self.assertEqual(fila['texto_evidencia'], 'Evidencia a')
        self.assertEqual(fila['pagina'], 2)
        self.assertEqual(fila['obra_clave'], 'Lomas de Ilo')
        self.assertEqual(len(self.consulta.actualizar(guardadas=True)), 1)
        self.assertEqual(len(self.consulta.actualizar()), 2)

    def test_vista_guardadas_no_permite_marcar_ni_guardar(self):
        self.seleccionados.guardar([self.a])
        self.consulta.actualizar(guardadas=True)
        self.consulta.alternar(self.a)
        self.consulta.seleccionar_todos()
        with self.assertRaises(ValueError):
            self.consulta.guardar()
        self.assertEqual(self.consulta.marcados, set())
        self.assertEqual(len(self.seleccionados.listar()), 1)

    def test_resultado_sin_precio_conserva_ausencia(self):
        self.consulta.actualizar()
        self.consulta.alternar(self.c)
        self.consulta.guardar()
        self.assertIsNone(self.seleccionados.listar()[0]['precio_unitario_texto'])


if __name__ == '__main__':
    unittest.main()

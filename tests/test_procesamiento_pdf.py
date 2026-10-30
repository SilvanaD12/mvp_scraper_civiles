"""Evita confundir montos globales con partidas y verifica procedencia/reprocesado."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfWriter

from sistema_costos.config.settings import Settings
from sistema_costos.database.candidatos_repository import CandidatosRepository
from sistema_costos.domain.partida_candidata import EstadoRevision
from sistema_costos.services.procesador_pdf import (
    detectar_terminos, extraer_partidas, procesar_pdf, PaginaExtraida, ResultadoPDF,
)
from sistema_costos.services.procesamiento_documentos import ProcesamientoDocumentos


CABECERA = 'Precios de Partidas\nCÓD. PARTIDA UND P .U. M.O. MAT. EQU. S/.\n'
FILA = 'OE.4.2.1.11* SALIDA DE AGUA FRIA PTO 139.01 118.05 17.42 3.54'


class ExtraccionTests(unittest.TestCase):
    def test_titulo_con_acentos_y_variantes(self):
        self.assertIn('Análisis de precios unitarios', detectar_terminos('ANÁLISIS DE PRECIOS UNITARIOS.pdf'))
        self.assertIn('APU', detectar_terminos('APUS - losa.pdf'))
        self.assertEqual(detectar_terminos('captura.pdf'), [])

    def test_conserva_precio_y_pagina_sin_inventar_metrado(self):
        filas = extraer_partidas('doc-1', 11, CABECERA + FILA)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0].pagina, 11)
        self.assertEqual(filas[0].precio_unitario_texto, '139.01')
        self.assertEqual(filas[0].texto_evidencia, FILA)
        self.assertEqual(filas[0].moneda, 'PEN')
        self.assertIsNone(filas[0].cantidad_texto)

    def test_no_convierte_monto_global_ni_tablas_sin_encabezado(self):
        self.assertEqual(extraer_partidas('d', 1, 'Valor estimado: S/ 800,000.00'), [])
        self.assertEqual(extraer_partidas('d', 1, FILA), [])
        self.assertEqual(extraer_partidas('d', 1, CABECERA + FILA.replace('139.01', '999.00')), [])

    def test_presupuesto_simple_con_metrado_y_total_comprobable(self):
        cabecera = 'PRESUPUESTO\nPartida UND Metrado Precio unitario Parcial\n'
        linea = '01.01 LIMPIEZA DE TERRENO M2 10.00 2.00 20.00'
        filas = extraer_partidas('d', 2, cabecera + linea)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0].cantidad_texto, '10.00')
        self.assertIsNone(filas[0].moneda)
        self.assertEqual(extraer_partidas('d', 2, cabecera + linea.replace('20.00', '90.00')), [])

    def test_pdf_sin_texto_no_genera_precios(self):
        with tempfile.TemporaryDirectory() as temp:
            ruta = Path(temp) / 'escaneo.pdf'
            writer = PdfWriter()
            writer.add_blank_page(width=200, height=200)
            writer.write(ruta)
            resultado = procesar_pdf(ruta, 'd', 'APU.pdf')
            self.assertEqual(resultado.estado, 'requiere_ocr')
            self.assertEqual(resultado.candidatos, [])

    def test_pdf_roto_da_error_comprensible(self):
        with tempfile.TemporaryDirectory() as temp:
            ruta = Path(temp) / 'roto.pdf'
            ruta.write_bytes(b'%PDF-1.7\nbroken')
            with self.assertRaises(ValueError):
                procesar_pdf(ruta, 'd', 'roto.pdf')


class PersistenciaTests(unittest.TestCase):
    def test_reprocesar_preserva_revision_evidencia_y_no_duplica(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            settings = Settings('Prueba', base / 'data', base / 'data/costos.db',
                                base / 'schema.sql', base / 'exports', base / 'logs')
            original = base / 'original.pdf'
            original.write_bytes(b'archivo de prueba aislado')
            servicio = ProcesamientoDocumentos(settings)

            def resultado(ruta, documento_id, titulo):
                texto = CABECERA + FILA
                return ResultadoPDF([PaginaExtraida(1, texto, detectar_terminos(texto))],
                                    extraer_partidas(documento_id, 1, texto))

            with patch('sistema_costos.services.procesamiento_documentos.procesar_pdf', side_effect=resultado):
                primero = servicio.procesar(original, obra_clave='obra-1')
                repo = CandidatosRepository(settings.database_path)
                id_candidato = repo.listar()[0]['id']
                repo.revisar(id_candidato, EstadoRevision.REVISADO, 'Revisor')
                segundo = servicio.procesar(original, obra_clave='obra-1')
            self.assertEqual(primero['documento_id'], segundo['documento_id'])
            self.assertEqual(len(repo.listar()), 1)
            self.assertEqual(repo.listar()[0]['estado'], 'revisado')
            self.assertEqual(repo.listar()[0]['obra_clave'], 'obra-1')
            self.assertEqual(len(servicio.listar()), 1)
            self.assertEqual(len(servicio.paginas(primero['documento_id'])), 1)
            self.assertTrue(Path(primero['ruta_local']).is_file())
            self.assertNotEqual(Path(primero['ruta_local']), original)


if __name__ == '__main__':
    unittest.main()

"""OCR selectivo, recuperación de errores y persistencia sin duplicados."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from pypdf import PdfWriter

from sistema_costos.config.settings import get_settings
from sistema_costos.services.ocr_pdf import ErrorOCR
from sistema_costos.services.procesador_pdf import procesar_pdf
from sistema_costos.services.procesamiento_documentos import ProcesamientoDocumentos
from sistema_costos.database.candidatos_repository import CandidatosRepository
from sistema_costos.database.partidas_seleccionadas_repository import PartidasSeleccionadasRepository

TEXTO = ('PRESUPUESTO S/\nPartida UND Metrado Precio unitario Parcial\n'
         '01.01 LIMPIEZA DE TERRENO M2 10.00 2.00 20.00')


class OCRTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.pdf = self.base / 'escaneo.pdf'
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.write(self.pdf)

    def test_ocr_recupera_texto_pagina_y_partida(self):
        with patch('sistema_costos.services.procesador_pdf.LectorOCR') as fabrica:
            lector = fabrica.return_value
            lector.idioma = 'spa'
            lector.leer_pagina.return_value = TEXTO
            resultado = procesar_pdf(self.pdf, 'doc', 'escaneo')
        self.assertEqual(resultado.paginas[0].metodo, 'ocr')
        self.assertEqual(resultado.candidatos[0].precio_unitario_texto, '2.00')
        self.assertEqual(resultado.candidatos[0].pagina, 1)
        lector.cerrar.assert_called_once()

    def test_pdf_digital_no_inicia_ocr(self):
        pagina = MagicMock()
        pagina.extract_text.return_value = 'PRESUPUESTO con texto digital'
        with patch('pypdf.PdfReader') as reader, patch(
                'sistema_costos.services.procesador_pdf.LectorOCR') as fabrica:
            reader.return_value.is_encrypted = False
            reader.return_value.pages = [pagina]
            resultado = procesar_pdf(self.pdf, 'doc', 'digital')
            fabrica.assert_not_called()
        self.assertEqual(resultado.paginas[0].metodo, 'texto_pdf')

    def test_falta_motor_informa_y_no_inventa_precios(self):
        with patch('sistema_costos.services.procesador_pdf.LectorOCR',
                   side_effect=ErrorOCR('No se encontró Tesseract OCR')):
            resultado = procesar_pdf(self.pdf, 'doc', 'escaneo')
        self.assertEqual(resultado.estado, 'requiere_ocr')
        self.assertEqual(resultado.candidatos, [])
        self.assertIn('No se encontró', resultado.avisos[0])

    def test_error_en_una_pagina_no_impide_recuperar_la_siguiente(self):
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.add_blank_page(width=200, height=200)
        writer.write(self.pdf)
        with patch('sistema_costos.services.procesador_pdf.LectorOCR') as fabrica:
            lector = fabrica.return_value
            lector.idioma = 'spa'
            lector.leer_pagina.side_effect = [ErrorOCR('Tiempo excedido'), TEXTO]
            resultado = procesar_pdf(self.pdf, 'doc', 'escaneo')
        self.assertEqual(resultado.paginas[0].metodo, 'sin_texto')
        self.assertEqual(resultado.paginas[1].metodo, 'ocr')
        self.assertEqual(resultado.candidatos[0].pagina, 2)
        lector.cerrar.assert_called_once()

    def test_reprocesar_conserva_identidad_seleccion_y_evidencia(self):
        settings = replace(get_settings(), data_dir=self.base/'datos',
                           database_path=self.base/'datos/costos.db')
        servicio = ProcesamientoDocumentos(settings)
        with patch('sistema_costos.services.procesador_pdf.LectorOCR') as fabrica:
            fabrica.return_value.idioma = 'spa'
            fabrica.return_value.leer_pagina.return_value = TEXTO
            primero = servicio.procesar(self.pdf)
            candidatos = CandidatosRepository(settings.database_path)
            seleccionados = PartidasSeleccionadasRepository(settings.database_path)
            seleccionados.guardar([candidatos.listar()[0]['id']])
            segundo = servicio.procesar(primero['ruta_local'], nombre=primero['nombre'],
                                       fuente=primero['fuente'], obra_clave=primero['obra_clave'])
        self.assertEqual(primero['documento_id'], segundo['documento_id'])
        self.assertEqual(len(candidatos.listar()), 1)
        self.assertEqual(len(seleccionados.listar()), 1)
        self.assertEqual(segundo['paginas_ocr'], [1])
        self.assertEqual(servicio.paginas(primero['documento_id'])[0]['texto'], TEXTO)


if __name__ == '__main__':
    unittest.main()

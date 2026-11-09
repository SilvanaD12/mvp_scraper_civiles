"""Regresiones de filas, montos no unitarios y archivos de descarga."""

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

from pypdf import PdfWriter

from sistema_costos.config.settings import get_settings
from sistema_costos.services.archivos_comprimidos import extraer_pdfs
from sistema_costos.services.extraccion_costos import contexto_textual, extraer_montos_generales
from sistema_costos.services.procesador_pdf import extraer_partidas, procesar_pdf
from sistema_costos.services.procesamiento_documentos import ProcesamientoDocumentos


TABLA = (
    'PRESUPUESTO\nÍtem Descripción Unidad Metrado Precio unitario Parcial\n'
    '01.01 PREPARACIÓN DE LOSA\nCON CONCRETO m2 12,50 37,40 467,50\n'
    '01.02 BASE GRANULAR m3 4,50 100,00 450,00'
)


class ExtraccionAvanceTests(unittest.TestCase):
    def test_tabla_con_descripcion_en_dos_lineas_y_decimal_coma(self):
        partidas = extraer_partidas('pdf', 4, TABLA)
        self.assertEqual(len(partidas), 2)
        self.assertEqual(partidas[0].descripcion, '01.01 PREPARACIÓN DE LOSA CON CONCRETO')
        self.assertEqual(partidas[0].unidad, 'm2')
        self.assertEqual(partidas[0].precio_unitario_texto, '37,40')
        self.assertEqual(partidas[0].cantidad_texto, '12,50')
        self.assertIn('\n', partidas[0].texto_evidencia)
        self.assertEqual(len(extraer_partidas('pdf', 4, TABLA.replace('467,50', '477,50'))), 1)

    def test_ocr_separa_filas_oe_y_conserva_el_texto_leido(self):
        lectura = ('0E.1.1.07 [CERCO | M| 12.00| 4.00| 7.00| 1.00]   '
                   'OE.2.1.08* [EXCAVACIÓN | M3| 20.00| 12.00| 5.00| 3.00]\n'
                   'OE.2.1.09* [EXCAVACIÓN H=1 M 25.00| 15.00| 5.00| 5.00]')
        hallazgos = extraer_partidas('pdf', 7, lectura, ocr=True)
        self.assertEqual([r.precio_unitario_texto for r in hallazgos], ['12.00', '20.00'])
        self.assertTrue(hallazgos[0].texto_evidencia.startswith('0E.'))
        self.assertEqual(extraer_partidas('pdf', 7, lectura), [])

    def test_montos_generales_conservan_tipo_y_no_son_precios_unitarios(self):
        texto = ('Costo directo: S/ 467,50\nPresupuesto contractual: USD 1,234.56\n'
                 'Inversión total\nS/ 1.234,56\nCosto directo unitario: S/ 20.00\n'
                 'Monto total de oferta: S/ 99.00\nValor referencial: 1.234')
        filas = extraer_montos_generales('pdf', 3, texto)
        self.assertEqual([f.tipo_monto for f in filas],
                         ['costo_directo', 'presupuesto_contractual', 'inversion_total'])
        self.assertEqual([f.moneda for f in filas], ['PEN', 'USD', 'PEN'])
        self.assertEqual(filas[2].monto_texto, '1.234,56')
        self.assertTrue(all(f.precio_unitario_texto is None and f.unidad is None for f in filas))

    def test_contexto_explicito_y_conflicto(self):
        self.assertEqual(contexto_textual('Obra: Losa Norte\nAño: 2025\nUbicación: Trujillo\nUbicación: Piura'),
                         {'obra': 'Losa Norte', 'anio': 2025})

    def test_layout_recupera_tabla_del_pdf_digital(self):
        pagina = MagicMock()
        pagina.extract_text.side_effect = lambda **kw: TABLA if kw else 'Presupuesto\nTexto desordenado'
        with TemporaryDirectory() as temp, patch('pypdf.PdfReader') as lector:
            ruta = Path(temp) / 'digital.pdf'
            ruta.touch()
            lector.return_value.is_encrypted = False
            lector.return_value.pages = [pagina]
            resultado = procesar_pdf(ruta, 'doc', 'presupuesto')
        self.assertEqual(len(resultado.candidatos), 2)
        self.assertEqual(resultado.candidatos[0].pagina, 1)


class ArchivoAvanceTests(unittest.TestCase):
    def test_zip_envia_pdf_a_extraccion_y_sqlite_sin_rutas_externas(self):
        with TemporaryDirectory() as temp:
            base = Path(temp)
            pdf = base / 'escaneo.pdf'
            writer = PdfWriter()
            writer.add_blank_page(width=200, height=200)
            writer.write(pdf)
            zip_path = base / 'expediente.zip'
            with ZipFile(zip_path, 'w') as zip_file:
                zip_file.write(pdf, 'presupuesto/scan.pdf')
                zip_file.write(pdf, '../fuera.pdf')
                zip_file.writestr('falso.pdf', 'No es un PDF')
                zip_file.writestr('nota.txt', 'Omitir')
            settings = replace(get_settings(), data_dir=base/'data', database_path=base/'data/costos.db')
            servicio = ProcesamientoDocumentos(settings)
            payload = {'fuente': 'SEACE', 'parent_key': 'obra-1',
                       'descarga': {'ruta_local': str(zip_path), 'documento': 'Expediente'},
                       'documento': {'publicado_en': '15/10/2025'},
                       'referencia': {'obra': {'nombre': 'Losa Norte', 'ubicacion': 'Trujillo'}}}
            with patch('sistema_costos.services.procesador_pdf.LectorOCR') as fabrica:
                fabrica.return_value.idioma = 'spa'
                fabrica.return_value.leer_pagina.return_value = TABLA + '\nCOSTO DIRECTO | S/ 917,50'
                resumen = servicio.procesar_descarga(payload)
            self.assertEqual(resumen['lote']['documentos_procesados'], 1)
            self.assertEqual(len(resumen['lote']['avisos']), 2)
            self.assertFalse((base/'fuera.pdf').exists())
            self.assertEqual(resumen['miembro_archivo'], 'presupuesto/scan.pdf')
            self.assertEqual(resumen['paginas_ocr'], [1])
            self.assertEqual(resumen['montos_generales'], 1)
            filas = servicio.repo.listar()
            self.assertEqual(len(filas), 3)
            self.assertTrue(all(f['obra'] == 'Losa Norte' and f['anio'] == 2025 and
                                f['lugar'] == 'Trujillo' for f in filas))

    def test_zip_invalido_produce_error_claro(self):
        with TemporaryDirectory() as temp:
            ruta = Path(temp) / 'dañado.zip'
            ruta.write_bytes(b'no es zip')
            with self.assertRaisesRegex(ValueError, 'ZIP'):
                extraer_pdfs(ruta, Path(temp)/'archivos')


if __name__ == '__main__':
    unittest.main()

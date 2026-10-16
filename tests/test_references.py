import copy
import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import MagicMock, patch

from sistema_costos.config.settings import Settings
from sistema_costos.database.references_repository import ReferencesRepository, procedure_identity
from sistema_costos.domain.obra_referencia import ObraReferencia
from sistema_costos.scrapers.seace import SeaceScraper, public_download_url
from sistema_costos.services.references_service import ReferencesService


class ReferencesTests(unittest.TestCase):
    def setUp(self):
        temp_root = Path(__file__).resolve().parents[1] / 'tmp' / 'tests'
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        assert Path(self.temp.name).resolve().is_relative_to(temp_root.resolve())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = Settings('test', self.root, self.root/'test.db', self.root/'schema.sql', self.root/'exports', self.root/'logs')
        self.store = ReferencesRepository(self.settings.database_path)

    def count(self, table):
        with closing(sqlite3.connect(self.settings.database_path)) as db:
            return db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def test_price_update_preserves_original_snapshot(self):
        row = {'nomenclatura': 'AS-1', 'entidad': 'Entidad', 'publicado_en': '2023-01-01', 'descripcion': 'Servicio', 'monto_texto': '100', 'moneda': 'PEN'}
        payload = {'fuente': 'SEACE', 'tipo': 'busqueda', 'asunto': 'obra', 'registros': [row]}
        first = self.store.save(copy.deepcopy(payload))
        row['monto_texto'] = '200'
        second = self.store.save(payload)
        self.assertEqual(self.store.get(first)['registros'][0]['monto_texto'], '100')
        self.assertEqual(self.store.get(second)['registros'][0]['monto_texto'], '200')
        self.assertEqual(self.count('seace_procedures'), 1)
        self.assertEqual(self.count('reference_events'), 2)

    def test_same_nomenclature_different_publication_keeps_both(self):
        rows = [{'nomenclatura': 'AS-1', 'entidad': 'Entidad', 'publicado_en': date} for date in ('2023-01-01', '2023-02-01')]
        self.store.save({'fuente': 'SEACE', 'tipo': 'busqueda', 'asunto': 'obra', 'registros': rows})
        self.assertEqual(self.count('seace_procedures'), 2)
        self.assertNotEqual(procedure_identity(rows[0]), procedure_identity(rows[1]))

    def test_download_history_keeps_versions_and_hash(self):
        service = ReferencesService(self.settings)
        doc = {'nombre': 'Documento', 'url_descarga': 'https://example.test/file.pdf'}
        detail = {'fuente': 'INFOBRAS', 'parent_key': '507544', 'documentos': [doc]}
        contents = b'%PDF-1.7\nfixture for download persistence only'
        def write(url, path):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)
            return path
        with patch('sistema_costos.services.references_service.DescargadorDocumentos.descargar_pdf', side_effect=write):
            first = service.download(detail, doc)
            second = service.download(detail, doc)
        self.assertNotEqual(first['descarga']['ruta_local'], second['descarga']['ruta_local'])
        self.assertEqual(first['descarga']['sha256'], hashlib.sha256(contents).hexdigest())
        self.assertEqual(self.count('document_downloads'), 2)
        metadata = json.loads(Path(first['descarga']['metadatos_local']).read_text(encoding='utf-8'))
        self.assertEqual(metadata['parent_key'], '507544')
        self.assertEqual(metadata['documento'], doc)

    def test_document_failure_preserves_infobras_fact_sheet(self):
        service = ReferencesService(self.settings)
        obra = ObraReferencia('INFOBRAS', '123', 'Obra ejemplo', 'https://example.test', '2026-10-16')
        with patch('sistema_costos.services.references_service.InfobrasScraper') as scraper:
            scraper.return_value.obtener_obra.return_value = obra
            scraper.return_value.listar_documentos.side_effect = OSError('Portal no disponible')
            data = service.detail_infobras('123')
        self.assertEqual(data['obra']['codigo_fuente'], '123')
        self.assertIn('Portal no disponible', data['aviso'])
        self.assertEqual(data['documentos'], [])
        self.assertEqual(service.obras.obtener('INFOBRAS', '123'), obra)

    def test_document_reordered_blocks_download_before_click(self):
        old = {'numero': '2', 'documento': 'Resumen ejecutivo', 'etapa': 'Convocatoria', 'publicado_en': '2023', 'archivo_texto': '1 KB'}
        new = dict(old, documento='Otro archivo', control_descarga_id='fresh-id')
        page = MagicMock()
        with self.assertRaisesRegex(ValueError, 'listado de documentos cambió'):
            SeaceScraper()._descargar_documento(page, [new], 2, self.root, esperado=old)
        page.expect_download.assert_not_called()

    def test_changed_procedure_blocks_opening(self):
        cells = ['0', 'Nueva entidad', '2023', 'AS-1', '', 'Servicio', 'Obra', '', '', '100', 'PEN', '', '']
        page = MagicMock()
        row = page.locator.return_value.filter.return_value
        row.count.return_value = 1
        row.inner_html.return_value = ''.join('<td>' + cell + '</td>' for cell in cells)
        with self.assertRaisesRegex(ValueError, 'resultado cambió'):
            SeaceScraper()._leer_ficha(page, 'AS-1', esperado={'nomenclatura': 'AS-1', 'entidad': 'Entidad anterior'})
        row.locator.assert_not_called()

    def test_download_url_omits_temporary_access_ticket(self):
        self.assertEqual(public_download_url('https://example.test/a.pdf?a=true&alf_ticket=secret&token=secret'), 'https://example.test/a.pdf?a=true')

    def test_empty_search_is_saved_and_recoverable(self):
        service = ReferencesService(self.settings)
        with patch('sistema_costos.services.references_service.BuscadorInfobras.buscar', return_value=(0, [])):
            result = service.search_infobras('ninguna')
        latest = service.store.recent()[0]
        self.assertEqual(service.store.get(latest['id'])['registros'], [])
        self.assertEqual(result['total'], 0)


if __name__ == '__main__':
    unittest.main()

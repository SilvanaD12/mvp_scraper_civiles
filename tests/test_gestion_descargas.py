from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from sistema_costos.config.settings import get_settings
from sistema_costos.database.connection import DatabaseConnection
from sistema_costos.database.partidas_seleccionadas_repository import PartidasSeleccionadasRepository
from sistema_costos.database.references_repository import ReferencesRepository
from sistema_costos.domain.partida_candidata import EstadoRevision, PartidaCandidata
from sistema_costos.services.gestion_descargas import GestionDescargas
from sistema_costos.services.procesamiento_documentos import ProcesamientoDocumentos


class GestionDescargasTests(unittest.TestCase):
    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.base = Path(temporal.name)
        self.settings = replace(get_settings(), data_dir=self.base,
                                database_path=self.base/'costos.db')
        self.historial = ReferencesRepository(self.settings.database_path)
        self.procesamiento = ProcesamientoDocumentos(self.settings)
        self.selecciones = PartidasSeleccionadasRepository(self.settings.database_path)
        self.gestion = GestionDescargas(self.settings)

    def archivo(self, ruta):
        archivo = self.base/'documentos'/ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_bytes(b'Archivo de prueba')
        return archivo

    def descarga(self, ruta, huella='a'*64):
        return self.historial.save({
            'tipo': 'descarga', 'fuente': 'SEACE', 'asunto': ruta.name, 'parent_key': 'obra',
            'descarga': {'ruta_local': str(ruta), 'sha256': huella, 'tamanio_bytes': ruta.stat().st_size},
        })

    def procesado(self, ruta, identificador, fuente):
        repo = self.procesamiento.repo
        repo.registrar_documento(identificador, ruta.name, str(ruta), fuente)
        candidato = repo.guardar(PartidaCandidata(identificador, 1, 'Partida', 'Texto'))
        repo.revisar(candidato, EstadoRevision.REVISADO)
        self.selecciones.guardar([candidato])
        with DatabaseConnection(self.settings.database_path) as db:
            db.execute('INSERT INTO paginas_pdf VALUES (?, 1, ?, ?)', (identificador, 'Texto', '[]'))
            db.execute('INSERT INTO procesamiento_pdf VALUES (?, ?, ?, ?)',
                       (identificador, 'candidatos_encontrados', 'hoy', '{}'))

    def test_limpia_pdf_y_dependencias_pero_conserva_carga_manual_y_zip(self):
        pdf = self.archivo('seace/descarga.pdf')
        metadata = self.archivo('seace/descarga.json')
        manual = self.archivo('manual/manual.pdf')
        zip_path = self.archivo('seace/expediente.zip')
        derivado = self.archivo(f'comprimidos/{"a"*64}/extraido.pdf')
        sin_registro = self.archivo('infobras/piloto.pdf')
        id_pdf = self.descarga(pdf, 'b'*64)
        id_zip = self.descarga(zip_path)
        id_consulta = self.historial.save({'fuente': 'INFOBRAS', 'tipo': 'busqueda', 'asunto': 'Prueba'})
        self.procesado(pdf, 'pdf', 'SEACE')
        self.procesado(derivado, 'derivado', 'SEACE')
        self.procesado(manual, 'manual', 'CARGA MANUAL')
        resultado = self.gestion.limpiar_pdfs()
        self.assertEqual((resultado.archivos, resultado.descargas, resultado.documentos_procesados), (3, 1, 2))
        self.assertTrue(all(not p.exists() for p in (pdf, metadata, derivado, sin_registro)))
        self.assertTrue(manual.is_file() and zip_path.is_file())
        with self.assertRaises(ValueError):
            self.historial.get(id_pdf)
        self.assertEqual(self.historial.get(id_zip)['tipo'], 'descarga')
        self.assertEqual(self.historial.get(id_consulta)['tipo'], 'busqueda')
        self.assertEqual([c['documento_id'] for c in self.selecciones.listar()], ['manual'])
        with DatabaseConnection(self.settings.database_path) as db:
            self.assertEqual(db.fetch_all('PRAGMA foreign_key_check'), [])
            self.assertEqual(db.fetch_one('SELECT COUNT(*) AS n FROM paginas_pdf')['n'], 1)

    def test_eliminar_zip_conserva_pdf_compartido_hasta_borrar_la_ultima_copia(self):
        primero = self.archivo('seace/a.zip')
        segundo = self.archivo('seace/b.zip')
        derivado = self.archivo(f'comprimidos/{"a"*64}/extraido.pdf')
        self.descarga(primero)
        self.descarga(segundo)
        self.procesado(derivado, 'derivado', 'SEACE')
        self.assertEqual(self.gestion.eliminar(primero).archivos, 1)
        self.assertTrue(derivado.is_file())
        self.assertEqual(self.gestion.eliminar(segundo).archivos, 2)
        self.assertFalse(derivado.exists())
        self.assertEqual(self.selecciones.listar(), [])

    def test_si_el_pdf_esta_bloqueado_restaurar_metadatos_y_registro(self):
        pdf = self.archivo('seace/descarga.pdf')
        metadata = self.archivo('seace/descarga.json')
        evento = self.descarga(pdf)
        original = type(pdf).replace
        bloqueado = pdf.resolve()

        def mover(ruta, destino):
            if ruta == bloqueado:
                raise PermissionError('PDF abierto')
            return original(ruta, destino)

        with patch.object(type(pdf), 'replace', mover), self.assertRaises(PermissionError):
            self.gestion.eliminar(pdf)
        self.assertTrue(pdf.is_file() and metadata.is_file())
        self.assertEqual(self.historial.get(evento)['tipo'], 'descarga')

    def test_rechaza_carga_manual(self):
        manual = self.archivo('manual/manual.pdf')
        with self.assertRaises(ValueError):
            self.gestion.eliminar(manual)
        self.assertTrue(manual.is_file())


if __name__ == '__main__':
    unittest.main()

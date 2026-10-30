"""Carga manual y descargas convergen en el mismo procesamiento y base SQLite."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from ..database.candidatos_repository import CandidatosRepository
from ..database.connection import DatabaseConnection
from .procesador_pdf import procesar_pdf


class ProcesamientoDocumentos:
    def __init__(self, settings):
        self.settings = settings
        self.repo = CandidatosRepository(settings.database_path)
        with DatabaseConnection(settings.database_path) as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS procesamiento_pdf (
                    documento_id TEXT PRIMARY KEY REFERENCES documentos_revision(id),
                    estado TEXT NOT NULL, procesado_en TEXT NOT NULL, resultado_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS paginas_pdf (
                    documento_id TEXT NOT NULL REFERENCES documentos_revision(id),
                    pagina INTEGER NOT NULL, texto TEXT NOT NULL, terminos_json TEXT NOT NULL,
                    PRIMARY KEY(documento_id, pagina)
                );
            ''')

    def procesar(self, ruta, nombre=None, fuente='CARGA MANUAL', obra_clave=None):
        ruta = Path(ruta).resolve()
        if ruta.suffix.lower() != '.pdf' or not ruta.is_file():
            raise ValueError('Seleccione un PDF. Descomprima los archivos ZIP o RAR antes de procesarlos.')
        nombre = nombre or ruta.name
        digest = self._huella(ruta)
        # Una carga manual se copia para conservar la evidencia aunque se mueva el original.
        if fuente == 'CARGA MANUAL':
            destino = self.settings.data_dir / 'documentos' / 'manual' / f'{digest}.pdf'
            destino.parent.mkdir(parents=True, exist_ok=True)
            if not destino.exists():
                shutil.copy2(ruta, destino)
            ruta = destino.resolve()
        datos_id = [str(ruta), digest, nombre, fuente, obra_clave]
        documento_id = hashlib.sha256(json.dumps(datos_id, ensure_ascii=False).encode()).hexdigest()
        resultado = procesar_pdf(ruta, documento_id, nombre)
        self.repo.registrar_documento(documento_id, nombre, str(ruta), fuente, obra_clave)
        for candidato in resultado.candidatos:
            self.repo.guardar(candidato)
        resumen = {
            'documento_id': documento_id, 'nombre': nombre, 'ruta_local': str(ruta),
            'fuente': fuente, 'obra_clave': obra_clave, 'sha256': digest,
            'estado': resultado.estado, 'paginas': len(resultado.paginas),
            'paginas_sin_texto': sum(not p.texto.strip() for p in resultado.paginas),
            'paginas_relevantes': [p.numero for p in resultado.paginas if p.terminos],
            'terminos_titulo': resultado.terminos_titulo,
            'terminos_contenido': sorted({t for p in resultado.paginas for t in p.terminos}),
            'candidatos': len(resultado.candidatos), 'avisos': resultado.avisos,
        }
        with DatabaseConnection(self.settings.database_path) as db:
            for pagina in resultado.paginas:
                db.execute('INSERT OR REPLACE INTO paginas_pdf VALUES(?,?,?,?)',
                           (documento_id, pagina.numero, pagina.texto, json.dumps(pagina.terminos, ensure_ascii=False)))
            db.execute('INSERT OR REPLACE INTO procesamiento_pdf VALUES(?,?,?,?)',
                       (documento_id, resultado.estado, datetime.now(timezone.utc).isoformat(),
                        json.dumps(resumen, ensure_ascii=False)))
        return resumen

    @staticmethod
    def _huella(ruta):
        digest = hashlib.sha256()
        with ruta.open('rb') as stream:
            for bloque in iter(lambda: stream.read(65536), b''):
                digest.update(bloque)
        return digest.hexdigest()

    def procesar_descarga(self, payload):
        info = payload['descarga']
        return self.procesar(info['ruta_local'], info['documento'], payload['fuente'], payload.get('parent_key'))

    def listar(self):
        with DatabaseConnection(self.settings.database_path) as db:
            return [json.loads(r['resultado_json']) for r in db.fetch_all(
                'SELECT resultado_json FROM procesamiento_pdf ORDER BY procesado_en DESC')]

    def paginas(self, documento_id):
        with DatabaseConnection(self.settings.database_path) as db:
            return [dict(r) for r in db.fetch_all(
                'SELECT * FROM paginas_pdf WHERE documento_id=? ORDER BY pagina', (documento_id,))]

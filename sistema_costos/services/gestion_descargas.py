"""Elimina descargas locales y sus resultados sin tocar consultas ni cargas manuales."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from uuid import uuid4

from ..database.connection import DatabaseConnection


@dataclass
class EliminacionDescargas:
    archivos: int = 0
    documentos_procesados: int = 0
    descargas: int = 0
    avisos: list[str] = field(default_factory=list)


class GestionDescargas:
    def __init__(self, settings):
        self.settings = settings
        self.raiz = settings.data_dir.resolve() / 'documentos'
        self.portales = (self.raiz / 'infobras', self.raiz / 'seace')
        self.comprimidos = self.raiz / 'comprimidos'

    def _administrada(self, ruta):
        original = Path(ruta)
        if not original.is_absolute() or original.is_symlink():
            return None
        ruta = original.resolve()
        if any(base in ruta.parents for base in (*self.portales, self.comprimidos)):
            return ruta
        return None

    def eliminar(self, ruta):
        """Elimina una descarga registrada, incluidos sus PDFs derivados exclusivos."""
        objetivo = self._administrada(ruta)
        if not objetivo or objetivo.suffix.lower() not in ('.pdf', '.zip', '.rar'):
            raise ValueError('Solo se pueden eliminar descargas administradas por la aplicación.')
        return self._eliminar(objetivo)

    def limpiar_pdfs(self):
        """Elimina los PDFs de portales y los extraídos de descargas comprimidas."""
        return self._eliminar(None)

    def _eliminar(self, objetivo):
        resultado = EliminacionDescargas()
        movidos = []
        temporal = self.settings.data_dir.resolve() / f'.eliminacion-{uuid4().hex}'
        try:
            with DatabaseConnection(self.settings.database_path) as db:
                db.execute('BEGIN IMMEDIATE')
                descargas = [(r, self._administrada(r['local_path'])) for r in db.fetch_all(
                    'SELECT id, local_path, sha256 FROM document_downloads')]
                carpeta_derivados = None
                if objetivo is None:
                    archivos = {ruta for _, ruta in descargas if ruta and ruta.suffix.lower() == '.pdf'}
                    for base in (*self.portales, self.comprimidos):
                        archivos.update(ruta for p in base.rglob('*') if p.suffix.lower() == '.pdf'
                                        and p.is_file() and (ruta := self._administrada(p)))
                else:
                    registro = next((r for r, ruta in descargas if ruta == objetivo), None)
                    if registro is None:
                        raise ValueError('Seleccione una descarga registrada.')
                    archivos = {objetivo}
                    huella = registro['sha256']
                    if (objetivo.suffix.lower() in ('.zip', '.rar') and re.fullmatch(r'[a-f0-9]{64}', huella)
                            and not any(r['sha256'] == huella and ruta != objetivo and ruta and ruta.is_file()
                                        for r, ruta in descargas)):
                        carpeta_derivados = self.comprimidos / huella
                        archivos.update(ruta for p in carpeta_derivados.glob('*.pdf')
                                        if (ruta := self._administrada(p)))

                tablas = {r['name'] for r in db.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")}
                documentos = []
                if 'documentos_revision' in tablas:
                    for r in db.fetch_all("SELECT id, ruta_local FROM documentos_revision WHERE fuente IN ('INFOBRAS', 'SEACE')"):
                        ruta = self._administrada(r['ruta_local'])
                        if objetivo is None and ruta and ruta.suffix.lower() == '.pdf':
                            archivos.add(ruta)
                        if ruta and carpeta_derivados and carpeta_derivados in ruta.parents:
                            archivos.add(ruta)
                        if ruta in archivos:
                            documentos.append(r['id'])

                # Apartar archivos primero. Si falla SQLite o hay un PDF abierto,
                # se devuelven a su ubicación y se revierte la operación.
                metadatos = {p.with_suffix('.json') for p in archivos
                             if any(base in p.parents for base in self.portales)}
                for archivo in sorted(archivos | metadatos):
                    if not archivo.is_file() or self._administrada(archivo) != archivo:
                        continue
                    temporal.mkdir(exist_ok=True)
                    destino = temporal / f'{len(movidos)}{archivo.suffix}'
                    archivo.replace(destino)
                    movidos.append((archivo, destino))
                    resultado.archivos += archivo in archivos

                for doc in documentos:
                    for tabla in ('partidas_seleccionadas', 'revisiones_candidatas'):
                        if tabla in tablas:
                            db.execute(f'DELETE FROM {tabla} WHERE candidato_id IN '
                                       '(SELECT id FROM partidas_candidatas WHERE documento_id=?)', (doc,))
                    for tabla in ('partidas_candidatas', 'paginas_pdf', 'procesamiento_pdf'):
                        if tabla in tablas:
                            db.execute(f'DELETE FROM {tabla} WHERE documento_id=?', (doc,))
                    db.execute('DELETE FROM documentos_revision WHERE id=?', (doc,))
                resultado.documentos_procesados = len(documentos)
                for fila, ruta in descargas:
                    if ruta in archivos:
                        db.execute('DELETE FROM document_downloads WHERE id=?', (fila['id'],))
                        resultado.descargas += 1
                for fila in db.fetch_all("SELECT id, payload_json FROM reference_events WHERE kind='descarga'"):
                    info = json.loads(fila['payload_json']).get('descarga') or {}
                    if info.get('ruta_local') and self._administrada(info['ruta_local']) in archivos:
                        db.execute('DELETE FROM reference_events WHERE id=?', (fila['id'],))
        except BaseException:
            for archivo, destino in reversed(movidos):
                destino.replace(archivo)
            if temporal.exists():
                temporal.rmdir()
            raise

        for _, destino in movidos:
            try:
                destino.unlink()
            except OSError:
                resultado.avisos.append(f'No se pudo borrar un archivo temporal en {temporal}.')
        if temporal.exists() and not resultado.avisos:
            temporal.rmdir()
        return resultado

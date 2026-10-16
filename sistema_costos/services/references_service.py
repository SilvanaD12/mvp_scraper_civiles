"""Casos de uso de la interfaz; las consultas guardadas no dependen de Internet."""

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..config.settings import Settings
from ..database.obras_repository import ObrasRepository
from ..database.references_repository import ReferencesRepository, procedure_identity
from ..scrapers.buscador_infobras import BuscadorInfobras
from ..scrapers.infobras import InfobrasScraper
from ..scrapers.seace import SeaceScraper
from .descargador_documentos import DescargadorDocumentos


class ReferencesService:
    def __init__(self, settings: Settings):
        self.settings = settings
        settings.ensure_directories()
        self.store = ReferencesRepository(settings.database_path)
        self.obras = ObrasRepository(settings.database_path)
        self.obras.inicializar()

    def _save(self, payload: dict) -> dict:
        self.store.save(payload)
        return payload

    def search_infobras(self, term: str, page: int = 1) -> dict:
        total, rows = BuscadorInfobras().buscar(term, page)
        return self._save({'fuente': 'INFOBRAS', 'tipo': 'busqueda',
                          'asunto': term, 'termino': term, 'pagina': page,
                          'total': total, 'registros': rows,
                          'url_busqueda': BuscadorInfobras.URL_BUSQUEDA})

    def detail_infobras(self, code: str) -> dict:
        scraper = InfobrasScraper()
        obra = scraper.obtener_obra(code)
        self.obras.guardar(obra)
        # The fact sheet remains usable if its document request fails.
        try:
            docs, warning = scraper.listar_documentos(code), ''
        except (OSError, ValueError, TimeoutError) as error:
            docs, warning = [], f'Ficha guardada; no se pudo consultar documentos: {error}'
        return self._save({'fuente': 'INFOBRAS', 'tipo': 'ficha',
                          'asunto': obra.nombre, 'codigo': code, 'parent_key': code,
                          'obra': asdict(obra), 'documentos': docs, 'aviso': warning})

    def search_seace(self, term: str, year: int) -> dict:
        self._check_year(year)
        data = SeaceScraper(headless=True).buscar(term, year)
        data.update(tipo='busqueda', asunto=f'{term} / {year}',
                    alcance='Primera página de resultados; no representa todas las coincidencias.')
        return self._save(data)

    def detail_seace(self, search: dict, procedure: dict) -> dict:
        data = SeaceScraper(headless=True).buscar(
            search['termino'], search['anio'], procedure['nomenclatura'],
            procedimiento_esperado=procedure)
        data.update(tipo='ficha', asunto=procedure['nomenclatura'],
                    procedimiento=procedure, parent_key=procedure_identity(procedure))
        return self._save(data)

    def download(self, detail: dict, document: dict) -> dict:
        source = detail['fuente']
        directory = self.settings.data_dir / 'documentos' / source.lower()
        if source == 'INFOBRAS':
            target = directory / f'{uuid4().hex}.pdf'
            path = DescargadorDocumentos().descargar_pdf(document['url_descarga'], target)
            info = {'ruta_local': str(path.resolve()), 'documento': document['nombre'],
                    'url_descarga': document['url_descarga'], 'extension': '.pdf',
                    'tamanio_bytes': path.stat().st_size}
        else:
            result = SeaceScraper(headless=True).buscar(
                detail['termino'], detail['anio'], detail['nomenclatura'],
                int(document['numero']), directory,
                procedimiento_esperado=detail['procedimiento'],
                documento_esperado=document)
            info = result['descarga']
            path = Path(info['ruta_local'])
        with path.open('rb') as stream:
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(65536), b''):
                digest.update(chunk)
            info['sha256'] = digest.hexdigest()
        payload = {'fuente': source, 'tipo': 'descarga',
                   'asunto': info['documento'], 'parent_key': detail['parent_key'],
                   'documento': document, 'referencia': detail,
                   'descarga': info, 'extraido_en': datetime.now(timezone.utc).isoformat()}
        metadata = path.with_suffix('.json')
        metadata.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        info['metadatos_local'] = str(metadata.resolve())
        return self._save(payload)

    @staticmethod
    def _check_year(year: int) -> None:
        if not 2000 <= year <= datetime.now().year:
            raise ValueError('Ingrese un año desde 2000 hasta el año actual.')

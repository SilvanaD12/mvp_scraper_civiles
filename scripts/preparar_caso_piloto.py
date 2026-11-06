"""Consulta real y opcional descarga del caso piloto. Alimenta el historial de la UI."""
import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fuente', choices=['infobras', 'seace', 'ambas'], default='ambas')
    parser.add_argument('--descargar', action='store_true')
    parser.add_argument('--bases', action='store_true', help='Descargar también Bases Integradas del caso SEACE')
    parser.add_argument('--verificar-limites', action='store_true', help='Comprobar consultas sin resultados y segunda página INFOBRAS')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.environ.setdefault('CENITEG_DATA_DIR', str(root / 'datos_locales'))
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(root / '.browsers'))
    from sistema_costos.config.settings import get_settings
    from sistema_costos.services.references_service import ReferencesService
    service = ReferencesService(get_settings())
    if args.verificar_limites:
        empty_info = service.search_infobras('ZZZCENITEGNORESULTADO20261016')
        assert empty_info['total'] == 0 and not empty_info['registros']
        empty_seace = service.search_seace('ZZZCENITEGNORESULTADO20261016', 2023)
        assert not empty_seace['registros']
        page = service.search_infobras('campamento', 2)
        assert page['pagina'] == 2 and page['registros']
        print('OK: consultas vacías INFOBRAS/SEACE y segunda página INFOBRAS.', flush=True)
        return
    if args.fuente in ('infobras', 'ambas'):
        search = service.search_infobras('campamento')
        print(f"INFOBRAS: {len(search['registros'])} filas, {search['total']} coincidencias", flush=True)
        detail = service.detail_infobras('507544')
        print(json.dumps(detail, ensure_ascii=False, indent=2), flush=True)
        if args.descargar and detail['documentos']:
            result = service.download(detail, detail['documentos'][0])
            print(json.dumps(result['descarga'], ensure_ascii=False), flush=True)

    if args.fuente in ('seace', 'ambas'):
        search = service.search_seace('CAMPAMENTOS', 2023)
        print(f"SEACE: {len(search['registros'])} filas", flush=True)
        matches = [r for r in search['registros'] if r['nomenclatura'] == 'AS-SM-16-2023-OEC/PERPG-GRMOQ-1']
        if len(matches) != 1:
            raise RuntimeError('El caso piloto no aparece de forma única en la primera página.')
        detail = service.detail_seace(search, matches[0])
        print(json.dumps(detail, ensure_ascii=False, indent=2), flush=True)
        if args.descargar:
            # Select by visible meaning, not a position hardcoded across procedures.
            matches = [d for d in detail['documentos'] if 'resumen' in d['documento'].lower()]
            if len(matches) != 1:
                raise RuntimeError('No se identificó un único Resumen ejecutivo.')
            result = service.download(detail, matches[0])
            print(json.dumps(result['descarga'], ensure_ascii=False), flush=True)
        if args.bases:
            matches = [d for d in detail['documentos'] if d['documento'].lower() == 'bases integradas']
            if len(matches) != 1:
                raise RuntimeError('No se identificaron unas únicas Bases Integradas.')
            result = service.download(detail, matches[0])
            print(json.dumps(result['descarga'], ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

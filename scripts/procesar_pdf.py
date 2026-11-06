"""Procesa un PDF local; usa la misma base y servicio que la aplicación."""

import argparse
import json

from sistema_costos.config.settings import get_settings
from sistema_costos.services.procesamiento_documentos import ProcesamientoDocumentos


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf')
    parser.add_argument('--obra')
    args = parser.parse_args()
    settings = get_settings()
    settings.ensure_directories()
    resultado = ProcesamientoDocumentos(settings).procesar(args.pdf, obra_clave=args.obra)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

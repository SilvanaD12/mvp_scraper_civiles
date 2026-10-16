import argparse
from urllib.error import URLError

from sistema_costos.scrapers.infobras import InfobrasScraper


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Listar documentos asociados a una obra de INFOBRAS."
    )
    parser.add_argument("--codigo", required=True)
    args = parser.parse_args()

    try:
        documentos = InfobrasScraper().listar_documentos(args.codigo)

        print(f"Documentos encontrados: {len(documentos)}\n")

        for numero, documento in enumerate(documentos, start=1):
            print(f"{numero}. {documento['nombre']}")
            print(f"Extensión: {documento['extension']}")
            print(f"Descarga: {documento['url_descarga']}")
            print()

    except (URLError, TimeoutError, ValueError) as error:
        parser.exit(status=1, message=f"Error: {error}\n")


if __name__ == "__main__":
    main()
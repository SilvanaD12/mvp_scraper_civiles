import argparse
import json
from pathlib import Path

from sistema_costos.scrapers.seace import SeaceScraper


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Leer documentos de una ficha SEACE guardada."
    )
    parser.add_argument("--html", type=Path, required=True)
    args = parser.parse_args()

    try:
        html = args.html.read_text(encoding="utf-8-sig")

        documentos = SeaceScraper.parsear_documentos_html(html)

        print(json.dumps(
            documentos,
            ensure_ascii=False,
            indent=2,
        ))
        print(f"\nDocumentos de esta página: {len(documentos)}")

    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(
            status=1,
            message=f"Error: {error}\n",
        )


if __name__ == "__main__":
    main()
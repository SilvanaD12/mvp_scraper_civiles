import argparse
import json

from playwright.sync_api import Error as PlaywrightError

from sistema_costos.scrapers.seace import SeaceScraper


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Consultar la primera página del buscador SEACE."
    )
    parser.add_argument("--termino", required=True)
    parser.add_argument("--anio", type=int, required=True)
    args = parser.parse_args()

    try:
        resultado = SeaceScraper().buscar(
            args.termino,
            args.anio,
        )

        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        print(
            "\nRegistros de esta página:",
            len(resultado["registros"]),
        )

    except (ValueError, RuntimeError, PlaywrightError) as error:
        parser.exit(status=1, message=f"Error: {error}\n")


if __name__ == "__main__":
    main()
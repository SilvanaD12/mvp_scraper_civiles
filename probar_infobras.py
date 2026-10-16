import json
from dataclasses import asdict
from urllib.error import URLError

from sistema_costos.scrapers.infobras import InfobrasScraper


def main() -> None:
    try:
        scraper = InfobrasScraper()
        obra = scraper.obtener_obra("507544")

        print(
            json.dumps(
                asdict(obra),
                ensure_ascii=False,
                indent=2,
            )
        )

    except (URLError, TimeoutError, ValueError) as error:
        print(f"No se pudo obtener la obra: {error}")


if __name__ == "__main__":
    main()
import argparse
import json
import sqlite3
from dataclasses import asdict
from urllib.error import URLError

from sistema_costos.config.settings import get_settings
from sistema_costos.database.connection import DatabaseError
from sistema_costos.database.obras_repository import ObrasRepository
from sistema_costos.scrapers.infobras import InfobrasScraper


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Consultar y guardar una ficha pública de INFOBRAS."
    )
    parser.add_argument(
        "--codigo",
        required=True,
        help="Código INFOBRAS de la obra.",
    )
    args = parser.parse_args()

    try:
        settings = get_settings()
        repositorio = ObrasRepository(settings.database_path)
        repositorio.inicializar()

        obra = InfobrasScraper().obtener_obra(args.codigo)
        repositorio.guardar(obra)

        print(json.dumps(asdict(obra), ensure_ascii=False, indent=2))
        print(f"\nReferencia guardada en: {settings.database_path}")
        print(f"Total de referencias: {repositorio.contar()}")

    except (
        URLError,
        TimeoutError,
        ValueError,
        DatabaseError,
        sqlite3.Error,
    ) as error:
        parser.exit(status=1, message=f"Error: {error}\n")


if __name__ == "__main__":
    main()
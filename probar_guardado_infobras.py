import json
import sqlite3
from dataclasses import asdict
from urllib.error import URLError

from sistema_costos.config.settings import get_settings
from sistema_costos.database.connection import DatabaseError
from sistema_costos.database.obras_repository import ObrasRepository
from sistema_costos.scrapers.infobras import InfobrasScraper


def main() -> None:
    settings = get_settings()
    repositorio = ObrasRepository(settings.database_path)

    try:
        repositorio.inicializar()

        obra = InfobrasScraper().obtener_obra("507544")

        repositorio.guardar(obra)
        cantidad_primera = repositorio.contar()

        # Guardamos otra vez para comprobar los duplicados.
        repositorio.guardar(obra)
        cantidad_segunda = repositorio.contar()

        recuperada = repositorio.obtener(
            obra.fuente,
            obra.codigo_fuente,
        )

        if recuperada != obra:
            raise ValueError(
                "Los datos recuperados no coinciden con los guardados."
            )

        if cantidad_primera != cantidad_segunda:
            raise ValueError(
                "El segundo guardado generó un duplicado."
            )

        print(f"Base de datos: {settings.database_path}")
        print(f"Registros tras primer guardado: {cantidad_primera}")
        print(f"Registros tras segundo guardado: {cantidad_segunda}")
        print("Verificación correcta: datos conservados sin duplicados.")

        print(
            json.dumps(
                asdict(recuperada),
                ensure_ascii=False,
                indent=2,
            )
        )

    except (
        URLError,
        TimeoutError,
        ValueError,
        DatabaseError,
        sqlite3.Error,
    ) as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()
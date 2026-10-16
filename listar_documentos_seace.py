import argparse
import json
from datetime import datetime, timezone

from playwright.sync_api import Error as PlaywrightError

from sistema_costos.config.settings import get_settings
from sistema_costos.scrapers.seace import SeaceScraper


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Abrir una ficha SEACE y listar sus documentos."
    )
    parser.add_argument("--termino", required=True)
    parser.add_argument("--anio", type=int, required=True)
    parser.add_argument("--nomenclatura", required=True)
    args = parser.parse_args()

    try:
        resultado = SeaceScraper().buscar(
            termino=args.termino,
            anio=args.anio,
            nomenclatura=args.nomenclatura,
        )

        fecha = datetime.now(timezone.utc)
        resultado["extraido_en"] = fecha.isoformat()

        texto = json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2,
        )

        settings = get_settings()
        settings.exports_dir.mkdir(parents=True, exist_ok=True)

        identificador = fecha.strftime("%Y%m%d_%H%M%S_%f")
        destino = (
            settings.exports_dir
            / f"documentos_seace_{identificador}.json"
        )

        with destino.open("x", encoding="utf-8") as archivo:
            archivo.write(texto)

        print(texto)
        print(
            "\nDocumentos de esta página:",
            len(resultado["documentos"]),
        )
        print(f"\nResultados guardados en: {destino}")

    except (
        ValueError,
        RuntimeError,
        PlaywrightError,
        OSError,
    ) as error:
        parser.exit(
            status=1,
            message=f"Error: {error}\n",
        )


if __name__ == "__main__":
    main()
import argparse
import json
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from sistema_costos.config.settings import get_settings
from sistema_costos.scrapers.seace import SeaceScraper


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descargar un documento de una ficha SEACE."
    )
    parser.add_argument("--termino", required=True)
    parser.add_argument("--anio", type=int, required=True)
    parser.add_argument("--nomenclatura", required=True)
    parser.add_argument("--numero", type=int, required=True)
    args = parser.parse_args()

    if args.numero < 1:
        parser.error("--numero debe ser mayor que cero.")

    try:
        settings = get_settings()
        carpeta = (
            settings.database_path.parent
            / "documentos"
            / "seace"
        )

        resultado = SeaceScraper().buscar(
            termino=args.termino,
            anio=args.anio,
            nomenclatura=args.nomenclatura,
            numero_documento=args.numero,
            carpeta_destino=carpeta,
        )

        destino = Path(
            resultado["descarga"]["ruta_local"]
        )
        metadatos = destino.with_suffix(".json")

        texto = json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2,
        )

        with metadatos.open("x", encoding="utf-8") as archivo:
            archivo.write(texto)

        print(texto)
        print(f"\nArchivo descargado en: {destino}")
        print(f"Metadatos guardados en: {metadatos}")

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
import argparse
import json
from datetime import datetime, timezone
from urllib.error import URLError

from sistema_costos.config.settings import get_settings
from sistema_costos.scrapers.infobras import InfobrasScraper
from sistema_costos.services.descargador_documentos import (
    DescargadorDocumentos,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descargar un documento de una obra de INFOBRAS."
    )
    parser.add_argument("--codigo", required=True)
    parser.add_argument("--numero", type=int, required=True)
    args = parser.parse_args()

    try:
        documentos = InfobrasScraper().listar_documentos(args.codigo)

        if not 1 <= args.numero <= len(documentos):
            raise ValueError(
                f"Seleccione un documento entre 1 y {len(documentos)}."
            )

        documento = documentos[args.numero - 1]
        settings = get_settings()

        carpeta = (
            settings.database_path.parent
            / "documentos"
            / args.codigo
        )

        fecha = datetime.now(timezone.utc)
        identificador = fecha.strftime("%Y%m%d_%H%M%S_%f")
        nombre = f"documento_{args.numero}_{identificador}"
        destino = carpeta / f"{nombre}.pdf"

        ruta = DescargadorDocumentos().descargar_pdf(
            documento["url_descarga"],
            destino,
        )

        # Conserva la procedencia junto al archivo.
        metadata = {
            **documento,
            "codigo_infobras": args.codigo,
            "descargado_en": fecha.isoformat(),
            "archivo_local": ruta.name,
        }

        with (carpeta / f"{nombre}.json").open(
            "x", encoding="utf-8"
        ) as archivo:
            json.dump(
                metadata,
                archivo,
                ensure_ascii=False,
                indent=2,
            )

        print(f"Documento: {documento['nombre']}")
        print(f"PDF guardado en: {ruta}")
        print("Procedencia guardada en el archivo JSON asociado.")

    except (URLError, TimeoutError, ValueError, OSError) as error:
        parser.exit(status=1, message=f"Error: {error}\n")


if __name__ == "__main__":
    main()
import argparse
import time
from datetime import datetime
from urllib.error import URLError

from sistema_costos.config.settings import get_settings
from sistema_costos.scrapers.buscador_infobras import BuscadorInfobras
from sistema_costos.services.candidatos_csv import CandidatosCSV


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exportar candidatos de INFOBRAS para revisión."
    )
    parser.add_argument("--termino", required=True)
    parser.add_argument("--paginas", type=int, default=2)
    args = parser.parse_args()

    if not 1 <= args.paginas <= 10:
        parser.error("Seleccione entre 1 y 10 páginas.")

    try:
        buscador = BuscadorInfobras()
        candidatos = {}
        total = 0

        for pagina in range(1, args.paginas + 1):
            total, obras = buscador.buscar(args.termino, pagina)

            print(f"Página {pagina}: {len(obras)} registros")

            for obra in obras:
                codigo = obra.get("Codigo")
                if codigo is None:
                    raise ValueError("Se recibió una obra sin código.")
                candidatos[str(codigo)] = obra

            if pagina * 20 >= total or not obras:
                break

            if pagina < args.paginas:
                time.sleep(1)

        settings = get_settings()
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        destino = settings.exports_dir / f"candidatos_infobras_{fecha}.csv"

        CandidatosCSV().exportar(list(candidatos.values()), destino)

        print(f"\nCoincidencias informadas por el portal: {total}")
        print(f"Candidatos únicos exportados: {len(candidatos)}")
        print(f"Archivo: {destino}")
        print("Los candidatos requieren revisión técnica.")

    except (URLError, TimeoutError, ValueError, KeyError, OSError) as error:
        parser.exit(status=1, message=f"Error: {error}\n")


if __name__ == "__main__":
    main()
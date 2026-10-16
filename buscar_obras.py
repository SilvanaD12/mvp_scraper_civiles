import argparse
from urllib.error import URLError

from sistema_costos.scrapers.buscador_infobras import BuscadorInfobras


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Buscar referencias de obras en INFOBRAS."
    )
    parser.add_argument("--termino", required=True)
    parser.add_argument("--pagina", type=int, default=1)
    args = parser.parse_args()

    try:
        total, obras = BuscadorInfobras().buscar(
            args.termino,
            args.pagina,
        )

        print(f"Coincidencias totales: {total}")
        print(f"Página consultada: {args.pagina}")
        print(f"Registros recibidos: {len(obras)}\n")

        for obra in obras:
            print(f"Código INFOBRAS: {obra.get('Codigo')}")
            print(f"Nombre: {obra.get('NombreObra')}")
            print(f"CUI: {obra.get('CUI')}")
            print(f"Estado: {obra.get('Estado')}")
            print("-" * 60)

    except (
        URLError,
        TimeoutError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        parser.exit(status=1, message=f"Error de búsqueda: {error}\n")


if __name__ == "__main__":
    main()
import csv
from pathlib import Path


class CandidatosCSV:
    COLUMNAS = [
        "codigo_infobras",
        "nombre",
        "cui",
        "estado",
        "url",
        "revision",
        "observaciones",
    ]

    def exportar(self, obras: list[dict], destino: Path) -> Path:
        destino.parent.mkdir(parents=True, exist_ok=True)

        # "x" evita sobrescribir un archivo existente.
        with destino.open("x", encoding="utf-8-sig", newline="") as archivo:
            writer = csv.DictWriter(
                archivo,
                fieldnames=self.COLUMNAS,
                delimiter=";",
            )
            writer.writeheader()

            for obra in obras:
                codigo = str(obra["Codigo"])

                fila = {
                    "codigo_infobras": codigo,
                    "nombre": obra.get("NombreObra") or "",
                    "cui": obra.get("CUI") or "",
                    "estado": obra.get("Estado") or "",
                    "url": (
                        "https://infobras.contraloria.gob.pe/"
                        f"InfobrasWeb/Mapa/Sumario?ObraId={codigo}"
                    ),
                    "revision": "Pendiente",
                    "observaciones": "",
                }

                # Evita interpretar texto externo como fórmula en Excel.
                for campo, valor in fila.items():
                    texto = str(valor)
                    if texto.lstrip().startswith(("=", "+", "-", "@")):
                        fila[campo] = "'" + texto

                writer.writerow(fila)

        return destino
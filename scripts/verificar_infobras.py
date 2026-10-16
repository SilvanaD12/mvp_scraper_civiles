from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from bs4 import BeautifulSoup


URL = (
    "https://infobras.contraloria.gob.pe/"
    "InfobrasWeb/Mapa/Sumario?ObraId=507544"
)


def main() -> None:
    try:
        with urlopen(URL, timeout=30) as response:
            status = response.status
            html = response.read()

        soup = BeautifulSoup(html, "html.parser")
        texto = soup.get_text(" ", strip=True)

        titulo = (
            soup.title.get_text(strip=True)
            if soup.title
            else "Sin título"
        )

        print(f"Estado HTTP: {status}")
        print(f"Página: {titulo}")
        print(f"URL consultada: {URL}")

        comprobaciones = {
            "Nombre del campamento": "CAMPAMENTOS DE CONTROL" in texto,
            "Código INFOBRAS": "507544" in texto,
            "Código de inversión": "2166595" in texto,
        }

        for campo, encontrado in comprobaciones.items():
            resultado = "Encontrado" if encontrado else "No encontrado"
            print(f"{campo}: {resultado}")

    except HTTPError as error:
        print(f"El servidor respondió con error HTTP {error.code}.")
    except URLError as error:
        print(f"No se pudo conectar: {error.reason}")
    except TimeoutError:
        print("La consulta superó el tiempo de espera.")


if __name__ == "__main__":
    main()
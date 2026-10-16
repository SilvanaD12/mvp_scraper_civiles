import json
from urllib.parse import urlencode
from urllib.request import urlopen


class BuscadorInfobras:
    URL_BUSQUEDA = (
        "https://infobras.contraloria.gob.pe/"
        "InfobrasWeb/Mapa/MapaEstadistico/BusquedaSimple"
    )

    def buscar(
        self,
        termino: str,
        pagina: int = 1,
    ) -> tuple[int, list[dict]]:
        termino = termino.strip()

        if not termino:
            raise ValueError("Ingrese un término de búsqueda.")

        if pagina < 1:
            raise ValueError("La página debe ser mayor o igual a 1.")

        parametros = urlencode({
            "nombre": termino,
            "codigo": "",
            "valor": "",
            "estado": "",
            "orderBy": "en_ejecucion",
            "pageNumber": pagina,
            "pageSize": 20,
        })

        with urlopen(
            f"{self.URL_BUSQUEDA}?{parametros}",
            timeout=30,
        ) as response:
            datos = json.load(response)

        if not isinstance(datos, dict):
            raise ValueError("INFOBRAS devolvió una respuesta inesperada.")

        resultados = datos.get("Result")
        parametros_respuesta = datos.get("Parameters")

        if not isinstance(resultados, list):
            raise ValueError("La respuesta no contiene una lista de obras.")

        if not isinstance(parametros_respuesta, dict):
            raise ValueError("Falta la información de paginación.")

        total = int(parametros_respuesta["records"])

        if not all(isinstance(obra, dict) for obra in resultados):
            raise ValueError("La lista contiene registros inesperados.")

        return total, resultados
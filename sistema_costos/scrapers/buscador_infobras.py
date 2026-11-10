import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


class InfobrasNoDisponible(RuntimeError):
    """El portal no pudo atender la búsqueda en vivo."""


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

        url = f"{self.URL_BUSQUEDA}?{parametros}"
        for intento, espera in enumerate((15, 25), 1):
            try:
                with urlopen(url, timeout=espera) as response:
                    datos = json.load(response)
                break
            except HTTPError as error:
                if error.code in (502, 503, 504) and intento == 1:
                    error.close()
                    continue
                error.close()
                raise InfobrasNoDisponible(
                    f"INFOBRAS no pudo atender la consulta (HTTP {error.code})."
                ) from error
            except (TimeoutError, URLError, ConnectionError) as error:
                motivo = error.reason if isinstance(error, URLError) else error
                if isinstance(motivo, (TimeoutError, ConnectionError)) and intento == 1:
                    continue
                mensaje = ("INFOBRAS tardó demasiado en responder."
                           if isinstance(motivo, TimeoutError)
                           else "No se pudo conectar con INFOBRAS.")
                raise InfobrasNoDisponible(mensaje) from error

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

from datetime import datetime, timezone
from urllib.request import urlopen

from bs4 import BeautifulSoup

from ..domain.obra_referencia import ObraReferencia


class InfobrasScraper:
    BASE_URL = (
        "https://infobras.contraloria.gob.pe/"
        "InfobrasWeb/Mapa/Sumario"
    )

    def obtener_obra(self, codigo: str) -> ObraReferencia:
        if not codigo.isdigit():
            raise ValueError("El código INFOBRAS debe ser numérico.")

        url = f"{self.BASE_URL}?ObraId={codigo}"

        with urlopen(url, timeout=30) as response:
            html = response.read().decode("utf-8-sig")

        return self.parsear_html(html, url, codigo)

    def parsear_html(
        self,
        html: str,
        url: str,
        codigo_esperado: str,
    ) -> ObraReferencia:
        soup = BeautifulSoup(html, "html.parser")

        nombre = self._leer_campo(soup, "NOMBRE DE OBRA")
        codigo = self._leer_campo(soup, "CÓDIGO INFOBRAS")

        if not nombre or codigo != codigo_esperado:
            raise ValueError(
                "La respuesta no contiene la ficha de obra esperada."
            )

        return ObraReferencia(
            fuente="INFOBRAS",
            codigo_fuente=codigo,
            nombre=nombre,
            url=url,
            extraido_en=datetime.now(timezone.utc).isoformat(),
            cui=self._leer_campo(
                soup, "CÓDIGO ÚNICO DE INVERSIÓN"
            ),
            entidad=self._leer_campo(
                soup, "ENTIDAD RESPONSABLE DE LA OBRA"
            ),
            ubicacion=self._leer_campo(
                soup, "UBICACIÓN GEOGRÁFICA"
            ),
            monto_aprobacion_texto=self._leer_campo(
                soup, "MONTO DE APROBACIÓN"
            ),
            fecha_aprobacion_texto=self._leer_campo(
                soup, "FECHA DE APROBACIÓN"
            ),
        )

    @staticmethod
    def _leer_campo(
        soup: BeautifulSoup,
        etiqueta: str,
    ) -> str | None:
        texto = soup.find(
            string=lambda valor: (
                valor is not None
                and " ".join(valor.split()) == etiqueta
            )
        )

        if texto is None:
            return None

        valor = texto.parent.find_next_sibling()

        if valor is None:
            return None

        return valor.get_text(" ", strip=True) or None
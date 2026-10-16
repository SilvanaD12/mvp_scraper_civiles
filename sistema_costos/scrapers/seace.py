from bs4 import BeautifulSoup
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


class SeaceScraper:
    URL = (
        "https://prod2.seace.gob.pe/seacebus-uiwd-pub/"
        "buscadorPublico/buscadorPublico.xhtml"
    )
    FORM = "tbBuscador:idFormBuscarProceso"
    TABLA = f"{FORM}:dtProcesos"

    def buscar(self, termino: str, anio: int) -> dict:
        termino = termino.strip()

        if not termino:
            raise ValueError("Ingrese un término de búsqueda.")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False)

            try:
                page = browser.new_page()
                page.set_default_timeout(30_000)

                page.goto(self.URL, wait_until="domcontentloaded")

                page.get_by_role(
                    "link",
                    name="Buscador de Procedimientos de Selección",
                    exact=True,
                ).click()

                page.locator(
                    f'[id="{self.FORM}:descripcionObjeto"]'
                ).fill(termino)

                # El control del portal contiene un select oculto.
                page.locator(
                    f'[id="{self.FORM}:anioConvocatoria_input"]'
                ).select_option(str(anio), force=True)

                cuerpo = page.locator(
                    f'[id="{self.TABLA}_data"]'
                )
                cuerpo.wait_for(state="visible")
                anterior = cuerpo.element_handle()

                page.locator(
                    f'[id="{self.FORM}:btnBuscarSelToken"]'
                ).click()

                # Espera a que la consulta reemplace la tabla anterior.
                page.wait_for_function(
                    "(anterior) => !anterior.isConnected",
                    arg=anterior,
                    timeout=60_000,
                )

                tabla = page.locator(f'[id="{self.TABLA}"]')
                tabla.wait_for(state="visible")

                return {
                    "fuente": "SEACE",
                    "termino": termino,
                    "anio": anio,
                    "url_busqueda": self.URL,
                    **self.parsear_tabla(tabla.inner_html()),
                }

            except PlaywrightTimeoutError as error:
                raise RuntimeError(
                    "SEACE no completó el flujo esperado. "
                    "Debemos revisar la carga, los controles "
                    "o una posible verificación del portal."
                ) from error

            finally:
                browser.close()

    @staticmethod
    def parsear_tabla(html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        cuerpo = soup.find("tbody")

        if cuerpo is None:
            raise ValueError("No se encontró la tabla de resultados.")

        paginacion = soup.select_one(".ui-paginator-current")
        registros = []

        for fila in cuerpo.find_all("tr", recursive=False):
            if "ui-datatable-empty-message" in fila.get("class", []):
                continue

            celdas = fila.find_all("td", recursive=False)

            if len(celdas) != 13:
                raise ValueError(
                    "La estructura de la tabla cambió; "
                    "se esperaban 13 columnas."
                )

            valores = [
                celda.get_text(" ", strip=True)
                for celda in celdas
            ]

            registros.append({
                "entidad": valores[1],
                "publicado_en": valores[2],
                "nomenclatura": valores[3],
                "objeto_contratacion": valores[5],
                "descripcion": valores[6],
                "cui_texto": valores[8],
                "monto_texto": valores[9],
                "moneda": valores[10],
            })

        return {
            "paginacion": (
                paginacion.get_text(" ", strip=True)
                if paginacion else None
            ),
            "registros": registros,
        }

    @staticmethod
    def parsear_documentos_html(
        html: str,
    ) -> list[dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")

        cuerpo = soup.find(
            "tbody",
            id="tbFicha:dtDocumentos_data",
        )

        if cuerpo is None:
            raise ValueError(
                "No se encontró la tabla de documentos SEACE."
            )

        documentos = []

        for fila in cuerpo.find_all("tr", recursive=False):
            if "ui-datatable-empty-message" in fila.get("class", []):
                continue

            celdas = fila.find_all("td", recursive=False)

            if len(celdas) != 6:
                raise ValueError(
                    "La estructura de documentos SEACE cambió."
                )

            enlace = celdas[3].select_one(
                'a[onclick*="descargaDocGeneral("]'
            )

            if enlace is None or not enlace.get("id"):
                raise ValueError(
                    "No se encontró el control de descarga."
                )

            documentos.append({
                "numero": celdas[0].get_text(" ", strip=True),
                "etapa": celdas[1].get_text(" ", strip=True),
                "documento": celdas[2].get_text(" ", strip=True),
                "archivo_texto": celdas[3].get_text(" ", strip=True),
                "publicado_en": celdas[4].get_text(" ", strip=True),
                "control_descarga_id": enlace["id"],
            })

        return documentos
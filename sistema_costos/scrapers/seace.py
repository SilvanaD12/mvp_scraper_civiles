from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import (
    Page,
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

    def buscar(
        self,
        termino: str,
        anio: int,
        nomenclatura: str | None = None,
        numero_documento: int | None = None,
        carpeta_destino: Path | None = None,
    ) -> dict:
        termino = termino.strip()

        if not termino:
            raise ValueError("Ingrese un término de búsqueda.")

        if nomenclatura is not None:
            nomenclatura = nomenclatura.strip()

            if not nomenclatura:
                raise ValueError(
                    "Ingrese la nomenclatura del procedimiento."
                )

        if numero_documento is not None:
            if numero_documento < 1:
                raise ValueError(
                    "El número de documento debe ser mayor que cero."
                )

            if nomenclatura is None:
                raise ValueError(
                    "Indique la nomenclatura para descargar un documento."
                )

            if carpeta_destino is None:
                raise ValueError(
                    "Indique la carpeta de descarga."
                )

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False)

            try:
                page = browser.new_page(accept_downloads=True)
                page.set_default_timeout(30_000)

                page.goto(
                    self.URL,
                    wait_until="domcontentloaded",
                )

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

                tabla = page.locator(
                    f'[id="{self.TABLA}"]'
                )
                tabla.wait_for(state="visible")

                if nomenclatura is not None:
                    resultado = {
                        "termino": termino,
                        "anio": anio,
                        "url_busqueda": self.URL,
                        **self._leer_ficha(page, nomenclatura),
                    }

                    if numero_documento is not None:
                        resultado["descarga"] = (
                            self._descargar_documento(
                                page=page,
                                documentos=resultado["documentos"],
                                numero=numero_documento,
                                carpeta=Path(carpeta_destino),
                            )
                        )

                    return resultado

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
                    "Debemos revisar la carga, los controles, "
                    "una posible verificación del portal "
                    "o si la descarga se abrió en otra ventana. "
                    f"Detalle: {error}"
                ) from error

            finally:
                browser.close()

    def _leer_ficha(
        self,
        page: Page,
        nomenclatura: str,
    ) -> dict:
        filas = page.locator(
            f'[id="{self.TABLA}_data"] > tr'
        )

        coincidencias = filas.filter(
            has=page.get_by_text(
                nomenclatura,
                exact=True,
            )
        )

        cantidad = coincidencias.count()

        if cantidad == 0:
            raise ValueError(
                "El procedimiento no aparece en la primera página "
                "de resultados para el término y año indicados."
            )

        if cantidad > 1:
            raise ValueError(
                "Hay varias filas con esa nomenclatura. "
                "Debemos diferenciarlas antes de abrir la ficha."
            )

        # Abre la ficha de la fila seleccionada.
        coincidencias.locator(
            'a:has(img[id$=":grafichaSel"])'
        ).click()

        panel = page.locator(
            '[id="tbFicha:pnlContenedorFicha1"]'
        )
        panel.wait_for(state="visible")

        # Comprueba que se abrió el procedimiento solicitado.
        soup = BeautifulSoup(
            panel.inner_html(),
            "html.parser",
        )

        etiqueta = soup.find(
            string=lambda texto: (
                texto is not None
                and texto.strip() == "Nomenclatura:"
            )
        )

        celda = (
            etiqueta.find_parent("td")
            if etiqueta is not None else None
        )

        valor = (
            celda.find_next_sibling("td")
            if celda is not None else None
        )

        nomenclatura_ficha = (
            valor.get_text(" ", strip=True)
            if valor is not None else None
        )

        if nomenclatura_ficha != nomenclatura:
            raise ValueError(
                "La ficha abierta no corresponde "
                "al procedimiento solicitado."
            )

        cuerpo = page.locator(
            '[id="tbFicha:dtDocumentos_data"]'
        )

        # Despliega la sección si está cerrada.
        if not cuerpo.is_visible():
            seccion = page.locator("fieldset").filter(
                has=page.get_by_text(
                    "Ver documentos por Etapa",
                    exact=True,
                )
            )
            seccion.locator("legend").click()

        cuerpo.wait_for(state="visible")

        tabla = page.locator(
            '[id="tbFicha:dtDocumentos"]'
        )

        documentos = self.parsear_documentos_html(
            tabla.inner_html()
        )

        return {
            "fuente": "SEACE",
            "nomenclatura": nomenclatura_ficha,
            "url_ficha": page.url,
            "alcance": "Primera página de documentos",
            "documentos": documentos,
        }

    def _descargar_documento(
        self,
        page: Page,
        documentos: list[dict[str, str]],
        numero: int,
        carpeta: Path,
    ) -> dict:
        coincidencias = [
            documento
            for documento in documentos
            if documento["numero"] == str(numero)
        ]

        if len(coincidencias) != 1:
            raise ValueError(
                "El número indicado no identifica un documento "
                "de la página actual."
            )

        documento = coincidencias[0]
        control_id = documento["control_descarga_id"]

        with page.expect_download(timeout=60_000) as evento:
            page.locator(
                f'[id="{control_id}"]'
            ).click()

        descarga = evento.value
        fallo = descarga.failure()

        if fallo:
            raise RuntimeError(
                f"SEACE no pudo completar la descarga: {fallo}"
            )

        temporal = descarga.path()

        if temporal is None:
            raise RuntimeError(
                "No se obtuvo el archivo descargado."
            )

        temporal = Path(temporal)
        tamanio = temporal.stat().st_size

        if tamanio == 0:
            raise ValueError(
                "El archivo descargado está vacío."
            )

        if tamanio > 25 * 1024 * 1024:
            raise ValueError(
                "El archivo supera el límite de 25 MB del MVP."
            )

        with temporal.open("rb") as archivo:
            cabecera = archivo.read(8)

        # Reconoce el formato mediante su cabecera.
        if cabecera.startswith(b"%PDF-"):
            extension = ".pdf"

        elif cabecera.startswith(
            (
                b"Rar!\x1a\x07\x00",
                b"Rar!\x1a\x07\x01\x00",
            )
        ):
            extension = ".rar"

        elif cabecera.startswith(
            (
                b"PK\x03\x04",
                b"PK\x05\x06",
                b"PK\x07\x08",
            )
        ):
            extension = ".zip"

        else:
            raise ValueError(
                "El archivo recibido no tiene una cabecera "
                "PDF, RAR o ZIP reconocida."
            )

        carpeta.mkdir(parents=True, exist_ok=True)

        fecha = datetime.now(timezone.utc)
        identificador = fecha.strftime("%Y%m%d_%H%M%S_%f")

        destino = carpeta / (
            f"documento_{numero}_{identificador}{extension}"
        )

        # Copia sin sobrescribir archivos existentes.
        try:
            with destino.open("xb") as salida:
                try:
                    with temporal.open("rb") as origen:
                        while bloque := origen.read(64 * 1024):
                            salida.write(bloque)

                except BaseException:
                    salida.close()
                    destino.unlink(missing_ok=True)
                    raise

        except FileExistsError:
            raise ValueError(
                "Ya existe un archivo con el nombre generado. "
                "Vuelva a ejecutar la descarga."
            ) from None

        return {
            "documento": documento["documento"],
            "numero": documento["numero"],
            "publicado_en": documento["publicado_en"],
            "nombre_original": descarga.suggested_filename,
            "url_descarga": descarga.url,
            "ruta_local": str(destino.resolve()),
            "extension": extension,
            "tamanio_bytes": tamanio,
            "descargado_en": fecha.isoformat(),
        }

    @staticmethod
    def parsear_tabla(html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        cuerpo = soup.find("tbody")

        if cuerpo is None:
            raise ValueError(
                "No se encontró la tabla de resultados."
            )

        paginacion = soup.select_one(
            ".ui-paginator-current"
        )
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
                if paginacion is not None else None
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
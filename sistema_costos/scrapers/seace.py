from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit, urlunsplit, parse_qsl, parse_qs, urlencode
from xml.etree import ElementTree


def public_download_url(url: str) -> str:
    """Conserva la ruta de procedencia sin credenciales temporales del portal."""
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if key.lower() not in ('alf_ticket', 'token', 'access_token')]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ''))

from bs4 import BeautifulSoup
from playwright.sync_api import (
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


class SeacePortalError(RuntimeError):
    """El portal no permitió completar una consulta verificable."""


class SeaceScraper:
    URL = (
        "https://prod2.seace.gob.pe/seacebus-uiwd-pub/"
        "buscadorPublico/buscadorPublico.xhtml"
    )
    FORM = "tbBuscador:idFormBuscarProceso"
    TABLA = f"{FORM}:dtProcesos"

    def __init__(self, headless: bool = False):
        self.headless = headless

    def buscar(
        self,
        termino: str,
        anio: int,
        nomenclatura: str | None = None,
        numero_documento: int | None = None,
        carpeta_destino: Path | None = None,
        procedimiento_esperado: dict | None = None,
        documento_esperado: dict | None = None,
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
            browser = playwright.chromium.launch(headless=self.headless)
            fallos = []
            etapa = 'crear la página del buscador'

            try:
                page = browser.new_page(accept_downloads=True)
                page.set_default_timeout(30_000)
                page.on('response', lambda respuesta: self._registrar_fallo(respuesta, fallos))
                etapa = 'cargar el portal'

                page.goto(
                    self.URL,
                    wait_until="domcontentloaded",
                )
                self._esperar_preparacion(page, fallos)

                etapa = 'preparar el buscador'
                page.get_by_role(
                    "link",
                    name="Buscador de Procedimientos de Selección",
                    exact=True,
                ).click()
                self._esperar_preparacion(page, fallos, formulario=True)

                page.locator(
                    f'[id="{self.FORM}:descripcionObjeto"]'
                ).fill(termino)

                # El control del portal contiene un select oculto.
                page.locator(
                    f'[id="{self.FORM}:anioConvocatoria_input"]'
                ).select_option(str(anio), force=True)

                etapa = 'ejecutar la búsqueda'
                self._consultar_tabla(page, fallos)

                tabla = page.locator(
                    f'[id="{self.TABLA}"]'
                )
                tabla.wait_for(state="visible")

                if nomenclatura is not None:
                    etapa = 'abrir la ficha seleccionada'
                    resultado = {
                        "termino": termino,
                        "anio": anio,
                        "url_busqueda": self.URL,
                        **self._leer_ficha(page, nomenclatura, procedimiento_esperado),
                    }

                    if numero_documento is not None:
                        etapa = 'descargar el documento seleccionado'
                        resultado["descarga"] = (
                            self._descargar_documento(
                                page=page,
                                documentos=resultado["documentos"],
                                numero=numero_documento,
                                carpeta=Path(carpeta_destino),
                                esperado=documento_esperado,
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
                self._comprobar_fallos(fallos)
                raise SeacePortalError(
                    f'SEACE agotó el tiempo al {etapa}. '
                    'No se confirmó una respuesta válida del portal. '
                    'Intente nuevamente o compruebe la consulta en el navegador.'
                ) from error

            finally:
                browser.close()

    @classmethod
    def _registrar_fallo(cls, respuesta, fallos):
        # No registra cookies, tokens, consultas ni identificadores de sesión.
        if (urlsplit(respuesta.url).hostname == urlsplit(cls.URL).hostname
                and respuesta.request.resource_type in ('document', 'script', 'xhr', 'fetch')
                and respuesta.status >= 400):
            fallos.append(respuesta.status)

    @staticmethod
    def _comprobar_fallos(fallos):
        if not fallos:
            return
        codigo = next((valor for valor in fallos if valor in (401, 403, 429)), fallos[0])
        if codigo in (401, 403):
            mensaje = 'SEACE rechazó el acceso a una solicitud o recurso del buscador'
        elif codigo == 429:
            mensaje = 'SEACE limitó la frecuencia de consultas; espere antes de volver a intentar'
        else:
            mensaje = 'SEACE no pudo cargar una solicitud o recurso necesario del buscador'
        raise SeacePortalError(
            f'{mensaje} (HTTP {codigo}). No se obtuvieron resultados nuevos. '
            'Compruebe el acceso al portal en el navegador y vuelva a intentar.'
        )

    @classmethod
    def _esperar_preparacion(cls, page, fallos, *, formulario=False, timeout_ms=30_000):
        limite = monotonic() + timeout_ms / 1000
        while True:
            cls._comprobar_fallos(fallos)
            listo = page.evaluate('''() =>
                typeof window.cargaTokenBuscadorProSel === 'function' &&
                typeof window.grecaptcha?.execute === 'function' &&
                typeof window.PrimeFaces?.ajax?.Queue?.isEmpty === 'function' &&
                window.PrimeFaces.ajax.Queue.isEmpty()
            ''')
            if listo and (not formulario or page.locator(
                    f'[id="{cls.FORM}:descripcionObjeto"]').is_visible()):
                return
            if monotonic() >= limite:
                raise SeacePortalError(
                    'SEACE cargó el buscador de forma incompleta: no están listos '
                    'sus controles, scripts o validación. No se envió la búsqueda. '
                    'Compruebe el portal en el navegador y vuelva a intentar.'
                )
            page.wait_for_timeout(200)

    @classmethod
    def _es_respuesta_busqueda(cls, respuesta):
        origen = urlsplit(respuesta.url)
        buscador = urlsplit(cls.URL)
        if (origen.hostname != buscador.hostname
                or origen.path.split(';')[0] != buscador.path):
            return False
        # La validación del portal también genera solicitudes binarias a otros
        # servicios. No se deben decodificar ni confundir con el formulario JSF.
        try:
            datos = parse_qs(respuesta.request.post_data or '')
        except UnicodeError:
            return False
        return datos.get('javax.faces.source') == [f'{cls.FORM}:btnBuscarSel']

    @classmethod
    def _validar_respuesta_busqueda(cls, texto):
        try:
            raiz = ElementTree.fromstring(texto)
        except ElementTree.ParseError as error:
            raise SeacePortalError('SEACE devolvió una respuesta distinta de la búsqueda esperada.') from error
        if raiz.tag != 'partial-response' or raiz.find('.//error') is not None:
            raise SeacePortalError('SEACE devolvió un error al ejecutar la búsqueda.')
        if raiz.find('.//redirect') is not None:
            raise SeacePortalError('SEACE solicitó recargar la sesión. Vuelva a realizar la búsqueda.')
        resultados = {f'{cls.FORM}:pnlGrdResultadosProcesos', cls.TABLA,
                      f'{cls.TABLA}_data', cls.FORM, 'tbBuscador'}
        if not any(elemento.get('id') in resultados for elemento in raiz.findall('.//update')):
            raise SeacePortalError(
                'SEACE respondió, pero no actualizó los resultados de la búsqueda. '
                'La consulta no se guardó; compruebe el portal en el navegador.'
            )

    @classmethod
    def _consultar_tabla(cls, page, fallos):
        # El botón visible ejecuta la validación normal del portal. Se espera la
        # respuesta de ESA búsqueda, no la desaparición de un elemento del DOM.
        cls._comprobar_fallos(fallos)
        with page.expect_response(cls._es_respuesta_busqueda, timeout=45_000) as evento:
            page.locator(f'[id="{cls.FORM}:btnBuscarSelToken"]').click()
        respuesta = evento.value
        cls._comprobar_fallos(fallos)
        if respuesta.status != 200:
            cls._comprobar_fallos([respuesta.status])
        cls._validar_respuesta_busqueda(respuesta.text())
        # PrimeFaces termina de aplicar la respuesta después de recibirla.
        cls._esperar_preparacion(page, fallos, formulario=True)

    def _leer_ficha(
        self,
        page: Page,
        nomenclatura: str,
        esperado: dict | None = None,
    ) -> dict:
        filas = page.locator(
            f'[id="{self.TABLA}_data"] > tr'
        )

        coincidencias = filas.filter(
            has=page.get_by_text(
                nomenclatura,
                exact=True,
            )
        ).element_handles()

        if not coincidencias:
            raise ValueError(
                "El procedimiento no aparece en la primera página "
                "de resultados para el término y año indicados."
            )

        if esperado is not None:
            claves = ('nomenclatura', 'entidad', 'publicado_en', 'descripcion',
                      'objeto_contratacion', 'cui_texto')

            def identidad(registro):
                return tuple(' '.join((registro.get(clave) or '').split()) for clave in claves)

            seleccionada = identidad(esperado)
            verificadas = []
            for fila in coincidencias:
                html = '<table><tbody><tr>' + fila.inner_html() + '</tr></tbody></table>'
                actual = self.parsear_tabla(html)['registros'][0]
                if identidad(actual) == seleccionada:
                    verificadas.append(fila)
            if not verificadas:
                raise ValueError('El resultado cambió desde la búsqueda. Busque de nuevo antes de abrir la ficha.')
            coincidencias = verificadas

        if len(coincidencias) > 1:
            raise ValueError(
                "SEACE muestra varias filas que no se pueden distinguir con los datos disponibles. "
                "Use una búsqueda más específica o abra la ficha en el portal."
            )

        # Conservamos el elemento verificado. Si la tabla se reemplaza,
        # el enlace se desprende en vez de apuntar a otra fila por posición.
        enlace = coincidencias[0].query_selector(
            'a:has(img[id$=":grafichaSel"])'
        )
        if enlace is None:
            raise ValueError('No se encontró el enlace de ficha en la fila seleccionada.')
        enlace.click()

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
        esperado: dict | None = None,
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
        if esperado is not None:
            keys = ('numero', 'etapa', 'documento', 'publicado_en', 'archivo_texto')
            if any(documento.get(key) != esperado.get(key) for key in keys):
                raise ValueError('El listado de documentos cambió. Abra la ficha otra vez antes de descargar.')
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
            "url_descarga": public_download_url(descarga.url),
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

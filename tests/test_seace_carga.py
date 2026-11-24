from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock
from urllib.parse import urlencode

from sistema_costos.scrapers.seace import SeacePortalError, SeaceScraper


class CargaSeaceTests(unittest.TestCase):
    def test_403_en_recurso_del_portal_impide_enviar_busqueda(self):
        respuesta = SimpleNamespace(
            url=SeaceScraper.URL, status=403,
            request=SimpleNamespace(resource_type='script'))
        fallos = []
        SeaceScraper._registrar_fallo(respuesta, fallos)
        page = MagicMock()
        with self.assertRaisesRegex(SeacePortalError, 'HTTP 403'):
            SeaceScraper._consultar_tabla(page, fallos)
        page.expect_response.assert_not_called()
        page.locator.assert_not_called()

    def test_error_de_analitica_externa_no_invalida_el_portal(self):
        respuesta = SimpleNamespace(
            url='https://analytics.example/collect', status=403,
            request=SimpleNamespace(resource_type='fetch'))
        fallos = []
        SeaceScraper._registrar_fallo(respuesta, fallos)
        self.assertEqual(fallos, [])

    def test_429_informa_limite_en_vez_de_esperar_resultados(self):
        with self.assertRaisesRegex(SeacePortalError, 'frecuencia.*HTTP 429'):
            SeaceScraper._comprobar_fallos([429])

    def test_solo_acepta_respuesta_de_la_busqueda_solicitada(self):
        def respuesta(origen, fuente):
            return SimpleNamespace(url=origen, request=SimpleNamespace(
                post_data=urlencode({'javax.faces.source': fuente})))
        fuente = f'{SeaceScraper.FORM}:btnBuscarSel'
        self.assertTrue(SeaceScraper._es_respuesta_busqueda(respuesta(SeaceScraper.URL, fuente)))
        self.assertFalse(SeaceScraper._es_respuesta_busqueda(respuesta(SeaceScraper.URL, 'tbBuscador')))
        self.assertFalse(SeaceScraper._es_respuesta_busqueda(respuesta('https://example.test', fuente)))

    def test_acepta_actualizacion_de_resultados_aunque_no_cambie_el_elemento(self):
        # El servidor puede actualizar el contenido de un tbody que permanece
        # conectado. La prueba verifica la respuesta, sin exigir su eliminación.
        for contenido in ('<tr><td>Resultado</td></tr>',
                          '<tr class="ui-datatable-empty-message"><td>Sin datos</td></tr>'):
            with self.subTest(contenido=contenido):
                SeaceScraper._validar_respuesta_busqueda(
                    '<partial-response><changes><update id="'
                    + SeaceScraper.TABLA + '_data"><![CDATA[' + contenido
                    + ']]></update></changes></partial-response>')

    def test_solicitudes_binarias_no_rompen_la_espera_de_resultados(self):
        class SolicitudBinaria:
            @property
            def post_data(self):
                raise UnicodeDecodeError('utf-8', b'\xf9', 0, 1, 'contenido binario')

        for url in ('https://www.google.com/recaptcha/api2/reload', SeaceScraper.URL):
            with self.subTest(url=url):
                self.assertFalse(SeaceScraper._es_respuesta_busqueda(
                    SimpleNamespace(url=url, request=SolicitudBinaria())))

    def test_mensaje_sin_resultados_nuevos_no_se_guarda_como_consulta_vacia(self):
        with self.assertRaisesRegex(SeacePortalError, 'no actualizó los resultados'):
            SeaceScraper._validar_respuesta_busqueda(
                '<partial-response><changes><update id="frmMesajes:gPrincipal">'
                'Validación no completada</update></changes></partial-response>')

    def test_sesion_expirada_y_respuesta_invalida_no_se_aceptan(self):
        for respuesta in ('<partial-response><redirect url="/login"/></partial-response>',
                          '<partial-response><error><error-name>Error</error-name></error></partial-response>',
                          '<html><body>Error de servidor</body></html>', 'no es XML'):
            with self.subTest(respuesta=respuesta), self.assertRaises(SeacePortalError):
                SeaceScraper._validar_respuesta_busqueda(respuesta)

    def test_scripts_incompletos_no_producen_falsos_resultados(self):
        page = MagicMock()
        page.evaluate.return_value = False
        with self.assertRaisesRegex(SeacePortalError, 'No se envió la búsqueda'):
            SeaceScraper._esperar_preparacion(page, [], timeout_ms=0)
        page.locator.assert_not_called()


if __name__ == '__main__':
    unittest.main()

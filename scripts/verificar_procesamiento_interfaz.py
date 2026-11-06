"""Comprobación local de la conexión UI/procesador. No usa portales ni base real."""

from dataclasses import replace
from pathlib import Path
import tempfile
import time

from pypdf import PdfWriter

from sistema_costos.config.settings import get_settings
from sistema_costos.ui.references_app import ReferencesApp


def main():
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        settings = replace(get_settings(), data_dir=base, database_path=base/'prueba.db',
                           exports_dir=base/'exports', logs_dir=base/'logs')
        ruta = base / 'sin_texto.pdf'
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.write(ruta)
        app = ReferencesApp(settings)
        try:
            app.update()
            errores = []
            app.show_error = lambda error: errores.append(str(error))
            app.run_task('Verificando PDF local', lambda: app.processing.service.procesar(ruta),
                         app.processing.completado)
            limite = time.monotonic() + 15
            while app.busy and time.monotonic() < limite:
                app.update()
                time.sleep(.01)
            assert not app.busy and not errores, errores
            assert app.processing.actual['estado'] == 'requiere_ocr'
            assert app.tabs.get() == 'Procesar PDFs'
            assert 'Sin texto' in app.processing.texto.get('1.0', 'end')
            # Priorizar títulos cambia el orden: la fila debe conservar el documento correcto.
            panel = app.panels['INFOBRAS']
            panel.detail_data = {'documentos': [
                {'nombre': 'Planos', 'numero': 1}, {'nombre': 'APU', 'numero': 2}]}
            panel.filtrar_documentos()
            assert panel.visible_docs[0]['numero'] == 2
            panel.solo_costos.select()
            panel.filtrar_documentos()
            assert len(panel.visible_docs) == 1
            print('OK: carga, hilo de procesamiento, reporte OCR, texto y filtro de documentos.')
        finally:
            app.destroy()


if __name__ == '__main__':
    main()

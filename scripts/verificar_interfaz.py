"""Prueba de integración local: widgets, trabajo en segundo plano e historial real.

No consulta portales ni descarga datos. Abre una ventana temporal y la cierra.
"""
import os
import time
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    os.environ.setdefault('CENITEG_DATA_DIR', str(root/'datos_locales'))
    from sistema_costos.config.settings import get_settings
    from sistema_costos.ui.references_app import ReferencesApp
    app = ReferencesApp(get_settings())
    try:
        app.update()
        errors = []
        app.show_error = lambda error: errors.append(str(error))
        entries = app.service.store.recent()
        for index in range(len(app.history_rows)):
            app.history.selection_set(str(index))
            app.show_history_payload()
            assert app.history_text.get('1.0', 'end').strip()
        checked = set()
        for entry in entries:
            key = entry['source'], entry['kind']
            if key in checked or entry['kind'] not in ('busqueda', 'ficha'):
                continue
            data = app.service.store.get(entry['id'])
            panel = app.panels[data['fuente']]
            app.tabs.set(data['fuente'])
            if data['tipo'] == 'busqueda':
                panel.show_search(data, saved=True)
                assert len(panel.results.get_children()) == len(data['registros'])
            else:
                panel.show_detail(data, saved=True)
                assert len(panel.documents.get_children()) == len(data['documentos'])
            checked.add(key)
            app.update()
        assert len(checked) == 4, f'Faltan consultas reales para comprobar: {checked}'
        results = []
        def job():
            time.sleep(0.15)
            return 'ok'
        app.run_task('Prueba de hilo', job, results.append)
        assert app.busy and all(button.cget('state') == 'disabled' for button in app.buttons)
        ticks = 0
        deadline = time.monotonic() + 5
        while app.busy and time.monotonic() < deadline:
            app.update()
            ticks += 1
            time.sleep(0.01)
        assert results == ['ok'] and ticks > 5 and not app.busy
        assert all(button.cget('state') == 'normal' for button in app.buttons)
        def fail():
            raise ValueError('Error de prueba controlado')
        app.run_task('Prueba de error', fail, results.append)
        deadline = time.monotonic() + 5
        while app.busy and time.monotonic() < deadline:
            app.update()
            time.sleep(0.01)
        assert errors == ['Error de prueba controlado'] and not app.busy
        print('OK: 4 vistas con datos reales, historial, hilo sin bloqueo y recuperación tras error.')
    finally:
        app.destroy()


if __name__ == '__main__':
    main()

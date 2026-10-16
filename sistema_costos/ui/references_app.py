"""Interfaz de referencias civiles. Solo el hilo principal toca los widgets."""

import json
import logging
import os
import queue
import threading
from pathlib import Path
from tkinter import messagebox, ttk, filedialog

import customtkinter as ctk

from ..services.references_service import ReferencesService

PILOT = 'AS-SM-16-2023-OEC/PERPG-GRMOQ-1'


def table(parent, columns, height=5):
    frame = ctk.CTkFrame(parent, fg_color='transparent')
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_rowconfigure(0, weight=1)
    tree = ttk.Treeview(frame, columns=[key for key, _, _ in columns], show='headings', height=height, selectmode='browse')
    for key, label, width in columns:
        tree.heading(key, text=label)
        tree.column(key, width=width, minwidth=60)
    tree.grid(row=0, column=0, sticky='nsew')
    ybar = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    ybar.grid(row=0, column=1, sticky='ns')
    xbar = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
    xbar.grid(row=1, column=0, sticky='ew')
    tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
    return frame, tree


def replace_rows(tree, rows):
    tree.delete(*tree.get_children())
    for index, row in enumerate(rows):
        tree.insert('', 'end', iid=str(index), values=row)


def set_text(widget, text):
    widget.configure(state='normal')
    widget.delete('1.0', 'end')
    widget.insert('1.0', text)
    widget.configure(state='disabled')


class PortalPanel(ctk.CTkFrame):
    def __init__(self, parent, app, source):
        super().__init__(parent, fg_color='transparent')
        self.app, self.source = app, source
        self.search_data = None
        self.detail_data = None
        self.grid_columnconfigure(0, weight=1)
        for row in (2, 4, 5):
            self.grid_rowconfigure(row, weight=1)
        controls = ctk.CTkFrame(self, fg_color='transparent')
        controls.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        ctk.CTkLabel(controls, text='Buscar obra' if source == 'INFOBRAS' else 'Buscar procedimiento').pack(side='left', padx=(0, 8))
        self.term = ctk.CTkEntry(controls, width=235)
        self.term.insert(0, 'campamento' if source == 'INFOBRAS' else 'CAMPAMENTOS')
        self.term.pack(side='left', padx=4)
        app.inputs.append(self.term)
        if source == 'SEACE':
            ctk.CTkLabel(controls, text='Año').pack(side='left', padx=(10, 3))
            self.year = ctk.CTkEntry(controls, width=70)
            self.year.insert(0, '2023')
            self.year.pack(side='left', padx=4)
            app.inputs.append(self.year)
        self.app.button(controls, 'Buscar', self.search).pack(side='left', padx=8)
        self.scope = ctk.CTkLabel(self, text='Primera página de resultados y documentos.' if source == 'SEACE' else 'Búsqueda pública de obras. Las fichas se guardan para volver a consultarlas.', anchor='w', text_color='#9DB1C6')
        self.scope.grid(row=1, column=0, sticky='ew')
        cols = [('code', 'Código INFOBRAS', 130), ('name', 'Obra', 620), ('cui', 'CUI', 110)] if source == 'INFOBRAS' else [
            ('code', 'Nomenclatura', 270), ('name', 'Descripción del procedimiento', 450), ('entity', 'Entidad', 240), ('date', 'Publicación', 130)]
        frame, self.results = table(self, cols)
        frame.grid(row=2, column=0, sticky='nsew', pady=4)
        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.grid(row=3, column=0, sticky='ew', pady=5)
        app.button(actions, 'Consultar selección', self.open_selected).pack(side='left', padx=(0, 8))
        if source == 'INFOBRAS':
            self.code = ctk.CTkEntry(actions, width=110, placeholder_text='Código')
            self.code.insert(0, '507544')
            self.code.pack(side='left', padx=4)
            app.inputs.append(self.code)
            app.button(actions, 'Consultar código', self.open_code).pack(side='left', padx=4)
            app.button(actions, 'Página anterior', lambda: self.page(-1)).pack(side='left', padx=4)
            app.button(actions, 'Siguiente página', lambda: self.page(1)).pack(side='left', padx=4)
        else:
            app.button(actions, 'Seleccionar caso piloto', self.select_pilot).pack(side='left', padx=4)
        self.info = ctk.CTkTextbox(self, height=112, wrap='word')
        self.info.grid(row=4, column=0, sticky='nsew', pady=(2, 5))
        set_text(self.info, 'Seleccione un resultado para ver su ficha y documentos.' +
                 ('\nCaso de referencia: campamentos de Lomas de Ilo, código 507544.' if source == 'INFOBRAS' else '\nCaso de referencia: ' + PILOT + '. Busque CAMPAMENTOS en 2023.'))
        frame, self.documents = table(self, [('number', 'N.º', 50), ('name', 'Documento', 520), ('stage', 'Etapa / formato', 190), ('date', 'Publicación', 140)], height=4)
        frame.grid(row=5, column=0, sticky='nsew', pady=4)
        bottom = ctk.CTkFrame(self, fg_color='transparent')
        bottom.grid(row=6, column=0, sticky='ew', pady=4)
        app.button(bottom, 'Descargar documento', self.download).pack(side='left', padx=(0, 8))
        app.button(bottom, 'Exportar ficha JSON', self.export).pack(side='left', padx=4)

    def search(self):
        term = self.term.get().strip()
        if not term:
            return self.app.notice('Ingrese un término de búsqueda.')
        if self.source == 'INFOBRAS':
            job = lambda: self.app.service.search_infobras(term)
        else:
            try:
                year = int(self.year.get())
                self.app.service._check_year(year)
            except ValueError:
                return self.app.notice('Ingrese un año válido desde 2000 hasta el año actual.')
            job = lambda: self.app.service.search_seace(term, year)
        self.clear_detail()
        self.search_data = None
        replace_rows(self.results, [])
        self.app.run_task('Buscando en ' + self.source + '…', job, self.show_search)

    def clear_detail(self):
        self.detail_data = None
        replace_rows(self.documents, [])
        set_text(self.info, 'Consulte una ficha para ver el detalle.')

    def show_search(self, data, saved=False):
        self.search_data = data
        self.clear_detail()
        rows = data['registros']
        if self.source == 'INFOBRAS':
            values = [(r.get('Codigo'), r.get('NombreObra'), r.get('CUI')) for r in rows]
            scope = f"{data['termino']} · Página {data['pagina']} · {len(rows)} resultados mostrados · {data['total']} coincidencias en el portal"
        else:
            values = [(r['nomenclatura'], r['descripcion'], r['entidad'], r['publicado_en']) for r in rows]
            scope = f"{data['termino']} / {data['anio']} · {len(rows)} resultados mostrados · Solo primera página · {data.get('paginacion') or ''}"
        replace_rows(self.results, values)
        self.scope.configure(text=('GUARDADO · ' if saved else 'Consulta realizada · ') + scope)
        if not rows:
            set_text(self.info, 'No se encontraron resultados en esta consulta. Cambie el término o el año.')
        self.app.status.configure(text=f"{len(rows)} resultados. Consulta {'recuperada' if saved else 'guardada'} · {data['extraido_en']}")

    def page(self, delta):
        if not self.search_data:
            return self.app.notice('Realice primero una búsqueda.')
        data = self.search_data
        page = data['pagina'] + delta
        if page < 1 or (page - 1) * 20 >= data['total']:
            return self.app.notice('No hay otra página en esa dirección.')
        self.app.run_task('Consultando página…', lambda: self.app.service.search_infobras(data['termino'], page), self.show_search)

    def open_code(self):
        code = self.code.get().strip()
        if not code.isdigit():
            return self.app.notice('Ingrese un código INFOBRAS numérico.')
        self.app.run_task('Consultando ficha y documentos…', lambda: self.app.service.detail_infobras(code), self.show_detail)

    def open_selected(self):
        selected = self.results.selection()
        if not selected or self.search_data is None:
            return self.app.notice('Seleccione una fila de resultados.')
        row = self.search_data['registros'][int(selected[0])]
        if self.source == 'INFOBRAS':
            code = str(row['Codigo'])
            job = lambda: self.app.service.detail_infobras(code)
        else:
            search = self.search_data
            job = lambda: self.app.service.detail_seace(search, row)
        self.app.run_task('Abriendo ficha y verificando la selección…', job, self.show_detail)

    def select_pilot(self):
        if self.search_data:
            matches = [i for i, r in enumerate(self.search_data['registros']) if r.get('nomenclatura') == PILOT]
            if len(matches) == 1:
                self.results.selection_set(str(matches[0]))
                self.results.see(str(matches[0]))
                return self.open_selected()
        self.app.notice('Busque CAMPAMENTOS, año 2023. El caso piloto debe aparecer una sola vez en la primera página.')

    def show_detail(self, data, saved=False):
        self.detail_data = data
        if self.source == 'INFOBRAS':
            r = data['obra']
            text = f"{r['nombre']}\nCódigo: {r['codigo_fuente']} · CUI: {r.get('cui') or 'Sin dato'}\nEntidad: {r.get('entidad') or 'Sin dato'}\nUbicación: {r.get('ubicacion') or 'Sin dato'}\nMonto publicado: {r.get('monto_aprobacion_texto') or 'Sin dato'} · Aprobación: {r.get('fecha_aprobacion_texto') or 'Sin dato'}\nFuente: {r['url']}"
        else:
            r = data['procedimiento']
            text = f"{r['nomenclatura']}\n{r['descripcion']}\nEntidad: {r['entidad']}\nMonto publicado: {r.get('monto_texto') or 'Sin dato'} {r.get('moneda') or ''} · Publicación: {r.get('publicado_en') or 'Sin dato'}\nFuente: {data['url_busqueda']}\nAlcance: primera página de documentos."
        text += '\nEste monto corresponde a la referencia publicada; no es una estimación de su proyecto.'
        if data.get('aviso'):
            text += '\n' + data['aviso']
        set_text(self.info, text)
        docs = data['documentos']
        replace_rows(self.documents, [(d.get('numero', i+1), d.get('documento', d.get('nombre')), d.get('etapa', d.get('extension', '')), d.get('publicado_en', '')) for i, d in enumerate(docs)])
        self.scope.configure(text=f"{'GUARDADO · ' if saved else ''}Ficha: {data['asunto']} · {data['extraido_en']}")
        self.app.status.configure(text=f"Ficha {'recuperada' if saved else 'guardada'} · {len(docs)} documentos listados." + (' ' + data.get('aviso', '') if data.get('aviso') else ''))

    def download(self):
        selected = self.documents.selection()
        if not selected or self.detail_data is None:
            return self.app.notice('Seleccione un documento de la ficha.')
        detail = self.detail_data
        doc = detail['documentos'][int(selected[0])]
        self.app.run_task('Descargando y registrando procedencia…', lambda: self.app.service.download(detail, doc), self.app.download_complete)

    def export(self):
        if self.detail_data is None:
            return self.app.notice('Consulte primero una ficha.')
        path = filedialog.asksaveasfilename(parent=self, title='Exportar ficha y fuentes', defaultextension='.json', initialfile=f'ficha_{self.source.lower()}.json', filetypes=[('JSON', '*.json')])
        if path:
            try:
                Path(path).write_text(json.dumps(self.detail_data, ensure_ascii=False, indent=2), encoding='utf-8')
                self.app.status.configure(text='Ficha exportada: ' + path)
            except OSError as error:
                self.app.show_error(error)


class ReferencesApp(ctk.CTk):
    def __init__(self, settings, service=None):
        super().__init__()
        self.settings = settings
        self.service = service or ReferencesService(settings)
        self.buttons, self.inputs = [], []
        self.events = queue.Queue()
        self.busy = False
        self.last_download = None
        self.title('Ceniteg | Referencias de obras civiles')
        self.geometry('1200x850')
        self.minsize(1050, 750)
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('blue')
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('Treeview', background='#17232F', foreground='#E1EAF2', fieldbackground='#17232F', rowheight=29, borderwidth=0)
        style.configure('Treeview.Heading', background='#24384B', foreground='white', font=('Segoe UI', 10, 'bold'))
        style.map('Treeview', background=[('selected', '#186CA4')], foreground=[('selected', 'white')])
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=22, pady=(16, 4))
        ctk.CTkLabel(header, text='CENITEG  /  Referencias civiles', font=ctk.CTkFont(size=25, weight='bold')).pack(side='left')
        self.button(header, 'Abrir carpeta de datos', lambda: self.open_path(settings.data_dir)).pack(side='right')
        ctk.CTkLabel(self, text='Busque obras, consulte sus documentos y conserve la fuente. Estimación de costos: pendiente de metrados, APUs y validación civil.', text_color='#B5C7D8', anchor='w').grid(row=1, column=0, sticky='ew', padx=22, pady=4)
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=2, column=0, sticky='nsew', padx=18, pady=6)
        self.panels = {}
        for source in ('INFOBRAS', 'SEACE'):
            tab = self.tabs.add(source)
            panel = PortalPanel(tab, self, source)
            panel.pack(fill='both', expand=True, padx=5, pady=4)
            self.panels[source] = panel
        self._build_history(self.tabs.add('Guardados'))
        footer = ctk.CTkFrame(self, fg_color='transparent')
        footer.grid(row=3, column=0, sticky='ew', padx=22, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        self.status = ctk.CTkLabel(footer, text='Listo. Empiece con INFOBRAS 507544 o busque CAMPAMENTOS en SEACE (2023).', anchor='w', wraplength=850)
        self.status.grid(row=0, column=0, sticky='w')
        self.button(footer, 'Abrir última descarga', self.open_last_download).grid(row=0, column=1, padx=5)
        self.progress = ctk.CTkProgressBar(footer, mode='indeterminate', height=4)
        self.progress.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(4, 0))
        self.progress.set(0)
        self.refresh_history()
        self.after(100, self._poll)
        self.protocol('WM_DELETE_WINDOW', self._close)

    def button(self, parent, text, command):
        widget = ctk.CTkButton(parent, text=text, command=command, height=30, width=130)
        self.buttons.append(widget)
        return widget

    def _build_history(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(parent, text='Consultas y descargas reales guardadas en este equipo. Reabrir una consulta no requiere Internet.', anchor='w').grid(row=0, column=0, sticky='ew', padx=8, pady=8)
        frame, self.history = table(parent, [('source', 'Fuente', 100), ('kind', 'Tipo', 100), ('subject', 'Referencia / búsqueda', 540), ('date', 'Fecha de consulta (UTC)', 230)], height=8)
        frame.grid(row=1, column=0, sticky='nsew', padx=8)
        bar = ctk.CTkFrame(parent, fg_color='transparent')
        bar.grid(row=2, column=0, sticky='ew', padx=8, pady=8)
        self.button(bar, 'Actualizar historial', self.refresh_history).pack(side='left', padx=4)
        self.button(bar, 'Reabrir selección', self.reopen).pack(side='left', padx=4)
        self.history_text = ctk.CTkTextbox(parent, wrap='word')
        self.history_text.grid(row=3, column=0, sticky='nsew', padx=8, pady=(0, 8))
        self.history.bind('<<TreeviewSelect>>', self.show_history_payload)

    def refresh_history(self):
        self.history_rows = self.service.store.recent()
        replace_rows(self.history, [(r['source'], r['kind'], r['subject'], r['created_at']) for r in self.history_rows])

    def history_payload(self):
        selected = self.history.selection()
        if not selected:
            raise ValueError('Seleccione una consulta o descarga del historial.')
        return self.service.store.get(self.history_rows[int(selected[0])]['id'])

    def show_history_payload(self, _event=None):
        try:
            payload = self.history_payload()
            lines = [payload['asunto'], '', 'Fuente: ' + payload['fuente'],
                     'Guardado el (UTC): ' + payload['extraido_en']]
            if payload['tipo'] == 'busqueda':
                lines += [f"Resultados guardados: {len(payload['registros'])}",
                          'Término: ' + payload['termino'],
                          'Use Reabrir selección para consultar esta lista sin conexión.']
            elif payload['tipo'] == 'ficha':
                row = payload.get('obra', payload.get('procedimiento', {}))
                lines += ['Entidad: ' + str(row.get('entidad') or 'Sin dato'),
                          'Monto publicado: ' + str(row.get('monto_aprobacion_texto', row.get('monto_texto')) or 'Sin dato'),
                          'El monto publicado no es una estimación para un proyecto nuevo.',
                          '', f"Documentos listados: {len(payload['documentos'])}"]
                lines += ['• ' + d.get('documento', d.get('nombre', 'Documento')) for d in payload['documentos']]
                lines += ['', 'Reabrir selección permite ver la ficha guardada. Descargar requiere Internet.']
            else:
                info = payload['descarga']
                lines += ['Documento: ' + info['documento'],
                          f"Tamaño: {info['tamanio_bytes']:,} bytes", 'Archivo: ' + info['ruta_local'],
                          'Procedencia: conservada en el JSON junto al archivo.',
                          'Huella SHA-256: ' + info['sha256'],
                          '', 'Reabrir selección abre el archivo local.']
            set_text(self.history_text, '\n'.join(lines))
        except ValueError:
            set_text(self.history_text, 'Seleccione un registro.')

    def reopen(self):
        try:
            data = self.history_payload()
            if data['tipo'] == 'descarga':
                self.last_download = Path(data['descarga']['ruta_local'])
                return self.open_last_download()
            panel = self.panels[data['fuente']]
            self.tabs.set(data['fuente'])
            if data['tipo'] == 'busqueda':
                panel.show_search(data, saved=True)
            else:
                panel.show_detail(data, saved=True)
        except (OSError, ValueError) as error:
            self.show_error(error)

    def run_task(self, label, job, complete):
        if self.busy:
            return
        self.busy = True
        for widget in self.buttons + self.inputs:
            widget.configure(state='disabled')
        self.status.configure(text=label)
        self.progress.start()

        def work():
            try:
                self.events.put((True, job(), complete))
            except Exception as error:
                logging.exception('Fallo en consulta de referencias')
                self.events.put((False, str(error), complete))
        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        try:
            ok, result, complete = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.progress.stop()
            self.progress.set(0)
            for widget in self.buttons + self.inputs:
                widget.configure(state='normal')
            try:
                if ok:
                    complete(result)
                    self.refresh_history()
                else:
                    self.show_error(result)
            except Exception as error:
                logging.exception('Fallo mostrando el resultado')
                self.show_error(error)
        self.after(100, self._poll)

    def download_complete(self, data):
        info = data['descarga']
        self.last_download = Path(info['ruta_local'])
        self.status.configure(text=f"Descargado: {info['documento']} · {info['tamanio_bytes']:,} bytes. Archivo, procedencia y huella SHA-256 guardados.")

    def open_last_download(self):
        if self.last_download is None:
            return self.notice('Descargue un documento o seleccione una descarga en Guardados.')
        self.open_path(self.last_download)

    def open_path(self, path):
        try:
            if not Path(path).exists():
                raise ValueError('El archivo ya no está en la ubicación guardada.')
            os.startfile(str(path))
        except (OSError, ValueError) as error:
            self.show_error(error)

    def notice(self, text):
        messagebox.showinfo('Referencias civiles', text, parent=self)

    def show_error(self, error):
        self.status.configure(text='La operación no terminó. Puede consultar los resultados anteriores en Guardados.')
        messagebox.showerror('No se pudo completar la operación', str(error)[:650] + '\n\nRevise su conexión e intente nuevamente. Si el portal solicita una verificación, requiere revisión manual.', parent=self)

    def _close(self):
        if self.busy:
            return self.notice('Hay una consulta o descarga en curso. Espere a que termine antes de cerrar.')
        self.destroy()

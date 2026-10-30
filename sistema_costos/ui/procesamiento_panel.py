"""Procesamiento local y consulta de páginas extraídas en la ventana principal."""

import os
from pathlib import Path
import subprocess
import sys
from tkinter import filedialog

import customtkinter as ctk

from ..services.procesamiento_documentos import ProcesamientoDocumentos


class ProcesamientoPanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color='transparent')
        from .references_app import table, set_text
        self.app, self.set_text = app, set_text
        self.service = ProcesamientoDocumentos(app.settings)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(5, weight=2)
        ctk.CTkLabel(self, text='Cargue un PDF o procese una descarga de Guardados. Los hallazgos requieren revisión.',
                     anchor='w').grid(row=0, column=0, sticky='ew', padx=6, pady=6)
        barra = ctk.CTkFrame(self)
        barra.grid(row=1, column=0, sticky='ew', pady=4)
        self.obra = ctk.CTkEntry(barra, placeholder_text='Obra / referencia de la carga manual', width=290)
        self.obra.pack(side='left', padx=6, pady=8)
        app.inputs.append(self.obra)
        app.button(barra, 'Cargar PDF', self.cargar).pack(side='left', padx=4)
        app.button(barra, 'Actualizar', self.actualizar).pack(side='left', padx=4)
        app.button(barra, 'Reprocesar / OCR', self.reprocesar).pack(side='left', padx=4)
        self.automatico = ctk.CTkCheckBox(barra, text='Procesar al descargar')
        self.automatico.select()
        self.automatico.pack(side='left', padx=10)
        app.inputs.append(self.automatico)
        frame, self.tabla = table(self, [('nombre', 'Documento', 360), ('fuente', 'Fuente', 120),
            ('estado', 'Resultado', 220), ('paginas', 'Páginas', 70), ('candidatos', 'Candidatos', 80)], height=5)
        frame.grid(row=2, column=0, sticky='nsew', pady=5)
        self.tabla.bind('<<TreeviewSelect>>', self.seleccionar)
        estado = ctk.CTkFrame(self, fg_color='transparent')
        estado.grid(row=3, column=0, sticky='ew', pady=4)
        estado.grid_columnconfigure(0, weight=1)
        self.resumen = ctk.CTkLabel(estado, text='Seleccione un documento.', anchor='w')
        self.resumen.grid(row=0, column=0, sticky='ew', padx=5)
        app.button(estado, 'Ver detalles', self.ver_detalles).grid(row=0, column=1, padx=5)
        self.detalles = ctk.CTkLabel(estado, text='', anchor='w', justify='left', wraplength=1000)
        self.detalles.grid(row=1, column=0, columnspan=2, sticky='ew', padx=5)
        self.detalles.grid_remove()
        controles = ctk.CTkFrame(self, fg_color='transparent')
        controles.grid(row=4, column=0, sticky='ew')
        ctk.CTkLabel(controles, text='Página del PDF:').pack(side='left', padx=5)
        self.selector = ctk.CTkOptionMenu(controles, values=['1'], command=self.mostrar_pagina)
        self.selector.pack(side='left', padx=5)
        self.busqueda = ctk.CTkEntry(controles, placeholder_text='Buscar en el texto extraído', width=250)
        self.busqueda.pack(side='left', padx=5)
        app.inputs.append(self.busqueda)
        app.button(controles, 'Buscar texto', self.buscar).pack(side='left', padx=5)
        app.button(controles, 'Abrir PDF', self.abrir).pack(side='left', padx=5)
        self.texto = ctk.CTkTextbox(self, wrap='word')
        self.texto.grid(row=5, column=0, sticky='nsew', pady=6)
        pie = ctk.CTkFrame(self, fg_color='transparent')
        pie.grid(row=6, column=0, sticky='ew', pady=4)
        app.button(pie, 'Revisar hallazgos', self.revisar).pack(side='left', padx=5)
        ctk.CTkLabel(pie, text='Guardar una selección no equivale a validar un precio para cotizar.',
                     text_color='#B5C7D8').pack(side='left', padx=10)
        self.filas, self.paginas, self.actual = [], [], None
        self.actualizar()

    def actualizar(self):
        from .references_app import replace_rows
        self.filas = self.service.listar()
        etiquetas = {'requiere_ocr': 'Requiere OCR / sin texto',
                     'candidatos_encontrados': 'Candidatos pendientes',
                     'sin_partidas_reconocidas': 'Sin partidas reconocidas'}
        replace_rows(self.tabla, [(r['nombre'], r['fuente'], etiquetas[r['estado']],
                                  r['paginas'], r['candidatos']) for r in self.filas])

    def cargar(self):
        ruta = filedialog.askopenfilename(parent=self, title='Cargar PDF de costos', filetypes=[('PDF', '*.pdf')])
        if not ruta:
            return
        obra = self.obra.get().strip() or None
        self.app.run_task('Leyendo PDF y buscando partidas…',
                          lambda: self.service.procesar(ruta, obra_clave=obra), self.completado)

    def procesar_descarga(self, payload):
        ruta = Path(payload['descarga']['ruta_local'])
        if ruta.suffix.lower() != '.pdf':
            return self.app.notice('La descarga se conservó. Descomprima el ZIP/RAR y cargue el PDF para procesarlo.')
        self.app.tabs.set('Procesar PDFs')
        self.app.run_task('Procesando documento descargado…',
                          lambda: self.service.procesar_descarga(payload), self.completado)

    def reprocesar(self):
        if not self.actual:
            return self.app.notice('Seleccione un documento para volver a procesarlo.')
        fila = dict(self.actual)
        self.app.run_task('Leyendo PDF y aplicando OCR a páginas sin texto…',
            lambda: self.service.procesar(fila['ruta_local'], nombre=fila['nombre'],
                fuente=fila['fuente'], obra_clave=fila.get('obra_clave')), self.completado)

    def completado(self, resultado):
        self.actualizar()
        for i, fila in enumerate(self.filas):
            if fila['documento_id'] == resultado['documento_id']:
                self.tabla.selection_set(str(i))
                self.tabla.see(str(i))
                self.seleccionar()
                break
        self.app.tabs.set('Procesar PDFs')
        self.app.status.configure(text=f"Procesado: {resultado['nombre']} · {resultado['candidatos']} candidatos pendientes de revisión.")

    def seleccionar(self, _evento=None):
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        self.actual = self.filas[int(seleccion[0])]
        self.paginas = self.service.paginas(self.actual['documento_id'])
        terminos = ', '.join(self.actual['terminos_contenido']) or 'ninguno'
        relevantes = ', '.join(map(str, self.actual['paginas_relevantes'])) or 'ninguna'
        self.detalles.configure(text=f"Contenido detectado: {terminos}. Páginas: {relevantes}.\n" +
                                ' '.join(self.actual['avisos']))
        self.detalles.grid_remove()
        total = self.actual['candidatos']
        resultado = f"{total} hallazgos para revisar" if total else 'Sin partidas reconocidas'
        self.resumen.configure(text=f"{self.actual['paginas']} páginas · {resultado}")
        valores = [str(p['pagina']) for p in self.paginas] or ['1']
        self.selector.configure(values=valores)
        primera = str(self.actual['paginas_relevantes'][0]) if self.actual['paginas_relevantes'] else valores[0]
        self.selector.set(primera)
        self.mostrar_pagina(primera)

    def ver_detalles(self):
        if not self.actual:
            return self.app.notice('Seleccione un documento procesado.')
        if self.detalles.winfo_ismapped():
            self.detalles.grid_remove()
        else:
            self.detalles.grid()

    def mostrar_pagina(self, numero):
        pagina = next((p for p in self.paginas if p['pagina'] == int(numero)), None)
        if pagina:
            self.set_text(self.texto, f"PÁGINA {numero} · {'Texto recuperado por OCR' if int(numero) in self.actual.get('paginas_ocr', []) else 'Texto del PDF'}\n\n" +
                          (pagina['texto'] or 'Sin texto extraíble. Esta página puede requerir OCR o estar vacía.'))

    def buscar(self):
        from ..services.procesador_pdf import normalizar
        termino = normalizar(self.busqueda.get().strip())
        if not termino:
            return self.app.notice('Ingrese el texto que desea buscar.')
        coincidencias = [p for p in self.paginas if termino in normalizar(p['texto'])]
        if not coincidencias:
            return self.app.notice('No se encontró el término en el texto extraído de este documento.')
        self.selector.set(str(coincidencias[0]['pagina']))
        self.mostrar_pagina(str(coincidencias[0]['pagina']))
        self.app.status.configure(text='Coincidencias en páginas: ' + ', '.join(str(p['pagina']) for p in coincidencias))

    def abrir(self):
        if self.actual:
            self.app.open_path(self.actual['ruta_local'])
        else:
            self.app.notice('Seleccione un documento procesado.')

    def revisar(self):
        entorno = os.environ.copy()
        entorno['CENITEG_DATA_DIR'] = str(self.app.settings.data_dir.resolve())
        opciones = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        subprocess.Popen([sys.executable, '-m', 'sistema_costos.ui.revision_candidatos_app'],
                         cwd=Path(__file__).resolve().parents[2], env=entorno, **opciones)

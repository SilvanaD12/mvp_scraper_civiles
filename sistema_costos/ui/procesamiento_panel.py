"""Documentos y resultados en una sola pantalla; OCR automático según cada página."""
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from ..database.candidatos_repository import CandidatosRepository
from ..database.partidas_seleccionadas_repository import PartidasSeleccionadasRepository
from ..services.procesamiento_documentos import ProcesamientoDocumentos
from ..services.revision_candidatos import RevisionCandidatosService
from ..services.consulta_resultados import ConsultaResultados


class ProcesamientoPanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color='transparent')
        from .references_app import table, set_text
        self.app, self.set_text = app, set_text
        self.service = ProcesamientoDocumentos(app.settings)
        ruta = app.settings.database_path
        self.revision = RevisionCandidatosService(
            CandidatosRepository(ruta), PartidasSeleccionadasRepository(ruta))
        self.consulta = ConsultaResultados(self.revision)
        self.filas, self.actual, self.ruta_pendiente = [], None, None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        barra = ctk.CTkFrame(self, fg_color='transparent')
        barra.grid(row=0, column=0, sticky='ew', pady=4)
        app.button(barra, 'Cargar PDF', self.cargar).pack(side='left', padx=4)
        app.button(barra, 'Procesar', self.procesar).pack(side='left', padx=4)
        app.button(barra, 'Actualizar', self.actualizar).pack(side='left', padx=4)
        self.automatico = ctk.CTkCheckBox(barra, text='Procesar al descargar')
        self.automatico.select()
        self.automatico.pack(side='left', padx=10)
        self.referencia = ctk.CTkEntry(barra, width=240, placeholder_text='Obra / referencia (opcional)')
        self.referencia.pack(side='left', padx=4, fill='x', expand=True)
        app.inputs.extend([self.automatico, self.referencia])
        self.resumen = ctk.CTkLabel(self, text='Cargue un PDF o seleccione un documento.', anchor='w')
        self.resumen.grid(row=1, column=0, sticky='ew', padx=5, pady=4)

        frame, self.tabla = table(self, [
            ('nombre', 'Documento', 510), ('fuente', 'Fuente', 130),
            ('estado', 'Resultado', 260), ('candidatos', 'Hallazgos', 90)], height=4)
        frame.grid(row=2, column=0, sticky='ew', pady=4)
        self.tabla.bind('<<TreeviewSelect>>', self.seleccionar)

        filtros = ctk.CTkFrame(self, fg_color='transparent')
        filtros.grid(row=3, column=0, sticky='ew', pady=6)
        self.vista = ctk.CTkOptionMenu(filtros,
            values=['Hallazgos sin incorporar', 'Datos guardados'], width=215,
            command=lambda _: self.actualizar_resultados())
        self.vista.pack(side='left', padx=4)
        self.ambito = ctk.CTkOptionMenu(filtros,
            values=['Documento seleccionado', 'Todos los documentos'], width=200,
            command=lambda _: self.actualizar_resultados())
        self.ambito.pack(side='left', padx=4)
        self.busqueda = ctk.CTkEntry(filtros, width=270,
            placeholder_text='Buscar descripción, obra o fuente')
        self.busqueda.pack(side='left', padx=4, fill='x', expand=True)
        self.busqueda.bind('<Return>', lambda _: self.actualizar_resultados())
        app.button(filtros, 'Buscar', self.actualizar_resultados).pack(side='left', padx=4)
        app.button(filtros, 'Limpiar', self.limpiar_busqueda).pack(side='left', padx=4)
        app.inputs.extend([self.vista, self.ambito, self.busqueda])

        frame, self.resultados = table(self, [
            ('elegir', 'Elegir', 70), ('descripcion', 'Descripción', 420),
            ('unidad', 'Unidad', 70), ('precio', 'Precio unitario', 130),
            ('moneda', 'Moneda', 80), ('fuente', 'Fuente', 100),
            ('obra', 'Obra / referencia', 260)], height=8)
        frame.grid(row=4, column=0, sticky='nsew', pady=4)
        self.resultados.column('elegir', stretch=False, anchor='center', minwidth=60)
        self.resultados.bind('<Button-1>', self.alternar_marca)

        pie = ctk.CTkFrame(self, fg_color='transparent')
        pie.grid(row=5, column=0, sticky='ew', pady=5)
        self.boton_todos = app.button(pie, 'Seleccionar visibles', self.seleccionar_todos)
        self.boton_todos.pack(side='left', padx=4)
        self.boton_guardar = app.button(pie, 'Guardar seleccionados', self.guardar)
        self.boton_guardar.pack(side='left', padx=4)
        self.boton_cancelar = app.button(pie, 'Cancelar selección', self.cancelar)
        self.boton_cancelar.pack(side='left', padx=4)
        app.button(pie, 'Detalles técnicos', self.ver_detalles).pack(side='right', padx=4)
        self.contador = ctk.CTkLabel(self, text='', anchor='w')
        self.contador.grid(row=6, column=0, sticky='ew', padx=5, pady=3)

        # Trazabilidad disponible bajo demanda, fuera de la tabla de uso habitual.
        self.detalle_frame = ctk.CTkFrame(self)
        self.detalle_frame.grid(row=7, column=0, sticky='ew', pady=4)
        self.detalle_frame.grid_columnconfigure(0, weight=1)
        self.detalle = ctk.CTkTextbox(self.detalle_frame, height=140, wrap='word')
        self.detalle.grid(row=0, column=0, sticky='ew', padx=6, pady=6)
        app.button(self.detalle_frame, 'Abrir PDF original', self.abrir).grid(row=0, column=1, padx=6)
        self.detalle_frame.grid_remove()
        self.resultados.bind('<<TreeviewSelect>>', self.mostrar_detalle)
        self.actualizar()

    def mensaje(self, texto):
        self.contador.configure(text=texto)

    def actualizar(self):
        conservar = self.actual.get('documento_id') if self.actual else None
        filas = self.service.listar()
        self.filas, self.actual = filas, None
        self.tabla.delete(*self.tabla.get_children())
        etiquetas = {'requiere_ocr': 'Requiere OCR / sin texto',
            'candidatos_encontrados': 'Hallazgos encontrados',
            'sin_partidas_reconocidas': 'Sin partidas reconocidas'}
        for fila in filas:
            self.tabla.insert('', 'end', iid=fila['documento_id'], values=(
                fila['nombre'], fila['fuente'], etiquetas.get(fila['estado'], fila['estado']),
                fila['candidatos']))
            if fila['documento_id'] == conservar:
                self.actual = fila
        if self.actual:
            self.tabla.selection_set(conservar)
        self.actualizar_resultados()

    def cargar(self):
        ruta = filedialog.askopenfilename(parent=self, title='Cargar PDF',
            filetypes=[('Documento PDF', '*.pdf')])
        if not ruta:
            return
        self.ruta_pendiente = Path(ruta)
        self.resumen.configure(text=f'Listo para procesar: {self.ruta_pendiente.name}')
        self.mensaje('Pulse Procesar para leer el PDF y obtener sus resultados.')

    def procesar(self):
        if self.ruta_pendiente:
            ruta = self.ruta_pendiente
            obra = self.referencia.get().strip() or None
            self.app.run_task('Procesando PDF…',
                lambda: self.service.procesar(ruta, obra_clave=obra), self.completado)
        elif self.actual:
            fila = dict(self.actual)
            self.app.run_task('Procesando documento…',
                lambda: self.service.procesar(fila['ruta_local'], nombre=fila['nombre'],
                    fuente=fila['fuente'], obra_clave=fila.get('obra_clave')), self.completado)
        else:
            self.mensaje('Cargue un PDF o seleccione un documento para procesar.')

    # Se mantiene el punto de entrada existente para descargas desde portales e historial.
    def procesar_descarga(self, payload):
        ruta = Path(payload['descarga']['ruta_local'])
        if ruta.suffix.lower() != '.pdf':
            return self.app.notice('La descarga se conservó. Descomprima el ZIP/RAR y cargue su PDF.')
        self.app.tabs.set('Procesar PDFs')
        self.app.run_task('Procesando documento descargado…',
            lambda: self.service.procesar_descarga(payload), self.completado)

    def reprocesar(self):
        self.procesar()

    def completado(self, resultado):
        self.ruta_pendiente = None
        self.referencia.delete(0, 'end')
        self.actual = resultado
        self.vista.set('Hallazgos sin incorporar')
        self.ambito.set('Documento seleccionado')
        self.busqueda.delete(0, 'end')
        self.actualizar()
        if self.actual:
            self.tabla.see(self.actual['documento_id'])
            self.seleccionar()
        self.app.tabs.set('Procesar PDFs')
        self.app.status.configure(text=f"Procesado: {resultado['nombre']} · {resultado['candidatos']} hallazgos.")

    def seleccionar(self, _evento=None):
        seleccion = self.tabla.selection()
        if not seleccion:
            return
        self.actual = next((f for f in self.filas if f['documento_id'] == seleccion[0]), None)
        if not self.actual:
            return
        self.ruta_pendiente = None
        self.resumen.configure(text=f"{self.actual['nombre']} · {self.actual['candidatos']} hallazgos")
        self.actualizar_resultados()

    def actualizar_resultados(self):
        if self.ambito.get() == 'Documento seleccionado' and not self.actual:
            self.consulta.cancelar()
            self.consulta.filas = {}
            self.resultados.delete(*self.resultados.get_children())
            self.mensaje('Seleccione un documento o elija Todos los documentos para consultar.')
            return
        doc = self.actual['documento_id'] if self.actual and self.ambito.get() == 'Documento seleccionado' else None
        try:
            filas = self.consulta.actualizar(
                guardadas=self.vista.get() == 'Datos guardados', documento_id=doc,
                termino=self.busqueda.get().strip())
        except Exception as error:
            self.app.show_error(error)
            return
        self.resultados.delete(*self.resultados.get_children())
        for f in filas:
            self.resultados.insert('', 'end', iid=f['id'], values=(
                'Guardado' if self.consulta.guardadas else '☐', f['descripcion'],
                f.get('unidad') or 'Sin extraer', f.get('precio_unitario_texto') or 'Sin extraer',
                f.get('moneda') or 'Sin registrar', f.get('fuente') or 'Sin registrar',
                f.get('obra_clave') or 'Sin registrar'))
        self.contar()
        self.mostrar_detalle()

    def contar(self):
        for boton in (self.boton_todos, self.boton_guardar, self.boton_cancelar):
            boton.configure(state='disabled' if self.consulta.guardadas or getattr(self.app, 'busy', False) else 'normal')
        self.mensaje(f"Resultados: {len(self.consulta.filas)} · " +
            ('Datos guardados' if self.consulta.guardadas else f'Seleccionados: {len(self.consulta.marcados)}'))

    def alternar_marca(self, evento):
        if getattr(self.app, 'busy', False) or self.consulta.guardadas:
            return
        if self.resultados.identify_region(evento.x, evento.y) != 'cell':
            return
        if self.resultados.identify_column(evento.x) != '#1':
            return
        clave = self.resultados.identify_row(evento.y)
        if not clave:
            return
        self.consulta.alternar(clave)
        self.resultados.set(clave, 'elegir', '☑' if clave in self.consulta.marcados else '☐')
        self.resultados.selection_set(clave)
        self.contar()
        return 'break'

    def seleccionar_todos(self):
        if getattr(self.app, 'busy', False) or self.consulta.guardadas:
            return
        self.consulta.seleccionar_todos()
        for clave in self.consulta.marcados:
            self.resultados.set(clave, 'elegir', '☑')
        self.contar()

    def cancelar(self):
        if getattr(self.app, 'busy', False) or self.consulta.guardadas:
            return
        self.consulta.cancelar()
        for clave in self.consulta.filas:
            self.resultados.set(clave, 'elegir', '☐')
        self.contar()
        self.mensaje('Selección cancelada. No se guardaron datos adicionales.')

    def guardar(self):
        if getattr(self.app, 'busy', False) or self.consulta.guardadas:
            return
        try:
            nuevos = self.consulta.guardar()
        except Exception as error:
            self.mensaje(str(error))
            return
        self.actualizar_resultados()
        self.mensaje(f'{nuevos} datos nuevos guardados. Consulte Datos guardados.')

    def limpiar_busqueda(self):
        self.busqueda.delete(0, 'end')
        self.actualizar_resultados()

    def ver_detalles(self):
        if self.detalle_frame.winfo_ismapped():
            self.detalle_frame.grid_remove()
        else:
            self.mostrar_detalle()
            self.detalle_frame.grid()

    def mostrar_detalle(self, _evento=None):
        ids = self.resultados.selection()
        f = self.consulta.filas.get(ids[0]) if ids else None
        if f:
            texto = '\n'.join(f'{label}: {f.get(key) or "Sin registrar"}' for label, key in (
                ('Documento', 'documento_nombre'), ('Página', 'pagina'), ('Fuente', 'fuente'),
                ('Obra', 'obra_clave'), ('Descripción', 'descripcion'), ('Unidad', 'unidad'),
                ('Precio unitario', 'precio_unitario_texto'), ('Moneda', 'moneda')))
            texto += '\n\nEvidencia original\n' + (f.get('texto_evidencia') or '')
        elif self.actual:
            texto = '\n'.join(self.actual.get('avisos', [])) or 'Seleccione un resultado para consultar su evidencia.'
        else:
            texto = 'Seleccione un documento o un resultado para consultar su procedencia.'
        self.set_text(self.detalle, texto)

    def abrir(self):
        ids = self.resultados.selection()
        try:
            if ids:
                ruta = self.revision.obtener_ruta_pdf(ids[0])
            elif self.actual:
                ruta = Path(self.actual['ruta_local'])
            else:
                return self.mensaje('Seleccione un resultado o un documento.')
            self.app.open_path(ruta)
        except (ValueError, OSError) as error:
            self.app.show_error(error)

    # Compatibilidad con el acceso anterior, sin crear otra ventana o proceso.
    def revisar(self):
        self.actualizar_resultados()
        self.resultados.focus_set()

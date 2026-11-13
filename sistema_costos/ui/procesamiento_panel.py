"""Documentos, resultados y filtros en una sola pantalla."""

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from ..database.candidatos_repository import CandidatosRepository
from ..database.partidas_seleccionadas_repository import (
    PartidasSeleccionadasRepository,
)
from ..services.procesamiento_documentos import ProcesamientoDocumentos
from ..services.revision_candidatos import RevisionCandidatosService
from ..services.consulta_resultados import ConsultaResultados


from costeo_mvp.partidas import precio_partida

from .tema import BORDE, DISPONIBLE, PANEL, SECUNDARIO, SUPERFICIE, TEXTO


class ProcesamientoPanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        from .references_app import table

        self.app = app
        self.service = ProcesamientoDocumentos(app.settings)

        ruta = app.settings.database_path
        self.revision = RevisionCandidatosService(
            CandidatosRepository(ruta),
            PartidasSeleccionadasRepository(ruta),
        )
        self.consulta = ConsultaResultados(self.revision)

        self.filas = []
        self.actual = None
        self.ruta_pendiente = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1, minsize=160)

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=4)

        app.button(barra, "Cargar PDF", self.cargar).pack(
            side="left", padx=4
        )
        self.boton_procesar = app.button(barra, "Procesar", self.procesar, variante="principal")
        self.boton_procesar.pack(side="left", padx=4)
        app.button(barra, "Actualizar", self.actualizar).pack(
            side="left", padx=4
        )

        self.boton_documentos = app.button(
            barra, "Ver documentos", self.alternar_documentos
        )
        self.boton_documentos.pack(side="left", padx=4)

        self.automatico = ctk.CTkCheckBox(
            barra, text="Procesar al descargar"
        )
        self.automatico.select()
        self.automatico.pack(side="left", padx=10)

        app.inputs.append(self.automatico)

        self.resumen = ctk.CTkLabel(
            self,
            text="Cargue un PDF y pulse Procesar, o consulte sus resultados guardados.",
            anchor="w",
        )
        self.resumen.grid(
            row=1, column=0, sticky="ew", padx=5, pady=4
        )

        self.documentos_frame = ctk.CTkFrame(self)
        self.documentos_frame.grid(row=2, column=0, sticky="ew", pady=4)
        self.documentos_frame.grid_columnconfigure(0, weight=1)

        self.referencia = ctk.CTkEntry(
            self.documentos_frame,
            placeholder_text="Obra / referencia opcional para la próxima carga",
        )
        self.referencia.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        app.inputs.append(self.referencia)

        frame, self.tabla = table(
            self.documentos_frame,
            [
                ("nombre", "Documento", 510),
                ("fuente", "Fuente", 130),
                ("estado", "Resultado", 260),
                ("candidatos", "Hallazgos", 90),
            ],
            height=3,
        )
        frame.grid(row=1, column=0, sticky="ew", padx=6, pady=4)
        self.tabla.bind("<<TreeviewSelect>>", self.seleccionar)
        self.documentos_frame.grid_remove()

        bloque_filtros = ctk.CTkFrame(
            self, fg_color="transparent"
        )
        bloque_filtros.grid(
            row=3, column=0, sticky="ew", pady=6
        )

        filtros = ctk.CTkFrame(
            bloque_filtros, fg_color="transparent"
        )
        filtros.pack(fill="x", pady=3)

        self.vista = ctk.CTkOptionMenu(
            filtros,
            values=["Hallazgos sin incorporar", "Datos guardados"],
            width=215, fg_color=SUPERFICIE, button_color=BORDE,
            text_color=TEXTO, button_hover_color=SECUNDARIO,
            command=lambda _: self.actualizar_resultados(),
        )
        self.vista.pack(side="left", padx=4)

        self.ambito = ctk.CTkOptionMenu(
            filtros,
            values=["Documento seleccionado", "Todos los documentos"],
            width=200, fg_color=SUPERFICIE, button_color=BORDE,
            text_color=TEXTO, button_hover_color=SECUNDARIO,
            command=lambda _: self.actualizar_resultados(),
        )
        self.ambito.pack(side="left", padx=4)
        self.ambito.set("Todos los documentos")

        self.busqueda = ctk.CTkEntry(
            filtros,
            width=240,
            placeholder_text="Buscar descripción, obra o fuente",
        )
        self.busqueda.pack(
            side="left", padx=4, fill="x", expand=True
        )

        app.button(
            filtros, "Buscar", self.actualizar_resultados
        ).pack(side="left", padx=4)
        app.button(
            filtros, "Limpiar", self.limpiar_busqueda
        ).pack(side="left", padx=4)

        contexto = ctk.CTkFrame(
            bloque_filtros, fg_color="transparent"
        )
        contexto.pack(fill="x", pady=3)

        ctk.CTkLabel(contexto, text="Filtrar por:").pack(
            side="left", padx=4
        )

        self.filtro_obra = ctk.CTkEntry(
            contexto,
            width=240,
            placeholder_text="Obra",
        )
        self.filtro_obra.pack(
            side="left", padx=4, fill="x", expand=True
        )

        self.filtro_anio = ctk.CTkEntry(
            contexto,
            width=100,
            placeholder_text="Año",
        )
        self.filtro_anio.pack(side="left", padx=4)

        self.filtro_lugar = ctk.CTkEntry(
            contexto,
            width=220,
            placeholder_text="Lugar",
        )
        self.filtro_lugar.pack(
            side="left", padx=4, fill="x", expand=True
        )

        for entrada in (
            self.busqueda,
            self.filtro_obra,
            self.filtro_anio,
            self.filtro_lugar,
        ):
            entrada.bind(
                "<Return>",
                lambda _: self.actualizar_resultados(),
            )

        app.inputs.extend([
            self.vista,
            self.ambito,
            self.busqueda,
            self.filtro_obra,
            self.filtro_anio,
            self.filtro_lugar,
        ])

        frame, self.resultados = table(
            self,
            [
                ("elegir", "Elegir", 70),
                ("descripcion", "Descripción", 380),
                ("unidad", "Unidad", 70),
                ("precio", "Precio unitario", 130),
                ("monto", "Monto general", 130),
                ("moneda", "Moneda", 80),
                ("fuente", "Fuente", 100),
                ("obra", "Obra / referencia", 240),
                ("anio", "Año", 80),
                ("lugar", "Lugar", 170),
            ],
            height=8,
        )
        frame.grid(row=4, column=0, sticky="nsew", pady=4)
        self.estado_vacio = ctk.CTkLabel(
            frame, text="", wraplength=600, fg_color=PANEL,
            text_color=SECUNDARIO,
        )

        self.resultados.column(
            "elegir",
            stretch=False,
            anchor="center",
            minwidth=60,
        )
        self.resultados.bind("<Button-1>", self.alternar_marca)
        self.resultados.bind("<<TreeviewSelect>>", self.resumir_resultado)

        pie = ctk.CTkFrame(self, fg_color="transparent")
        pie.grid(row=5, column=0, sticky="ew", pady=5)

        self.acciones_hallazgos = ctk.CTkFrame(pie, fg_color="transparent")
        self.boton_guardar = app.button(
            self.acciones_hallazgos, "Guardar selección", self.guardar, variante="principal"
        )
        self.boton_guardar.pack(side="left", padx=4)

        self.boton_todos = app.button(
            self.acciones_hallazgos, "Marcar visibles", self.seleccionar_todos
        )
        self.boton_todos.pack(side="left", padx=4)

        self.boton_cancelar = app.button(
            self.acciones_hallazgos, "Desmarcar todo", self.cancelar
        )
        self.boton_cancelar.pack(side="left", padx=4)

        self.boton_estimar = app.button(
            pie, "Enviar al estimador", self.enviar_estimador,
            variante="principal", registrar=False,
        )

        self.contador = ctk.CTkLabel(
            self, text="", anchor="w", text_color=TEXTO
        )
        self.contador.grid(
            row=6, column=0, sticky="ew", padx=5, pady=3
        )

        self.ayuda_acciones = ctk.CTkLabel(self, text="", text_color=SECUNDARIO, anchor="w")
        self.ayuda_acciones.grid(row=7, column=0, sticky="ew", padx=5)

        self.actualizar()

    def alternar_documentos(self):
        if self.documentos_frame.winfo_ismapped():
            self.documentos_frame.grid_remove()
            self.boton_documentos.configure(text="Ver documentos")
        else:
            self.documentos_frame.grid()
            self.boton_documentos.configure(text="Ocultar documentos")

    def mensaje(self, texto):
        self.contador.configure(text=texto)

    def actualizar(self):
        conservar = (
            self.actual.get("documento_id")
            if self.actual else None
        )
        self.filas = self.service.listar()
        self.actual = None
        self.tabla.delete(*self.tabla.get_children())

        etiquetas = {
            "requiere_ocr": "Requiere OCR / sin texto",
            "candidatos_encontrados": "Hallazgos encontrados",
            "sin_partidas_reconocidas": "Sin partidas reconocidas",
        }

        for fila in self.filas:
            self.tabla.insert(
                "",
                "end",
                iid=fila["documento_id"],
                values=(
                    fila["nombre"],
                    fila["fuente"],
                    etiquetas.get(fila["estado"], fila["estado"]),
                    fila["candidatos"],
                ),
            )
            if fila["documento_id"] == conservar:
                self.actual = fila

        if self.actual:
            self.tabla.selection_set(conservar)
        elif conservar:
            self.resumen.configure(text="Seleccione un documento.")

        self.actualizar_resultados()

    def cargar(self):
        ruta = filedialog.askopenfilename(
            parent=self,
            title="Cargar PDF",
            filetypes=[("Documento PDF", "*.pdf")],
        )
        if not ruta:
            return

        self.ruta_pendiente = Path(ruta)
        self.actual = None
        self.tabla.selection_remove(*self.tabla.selection())
        self.ambito.set("Documento seleccionado")
        self.actualizar_resultados()
        self.resumen.configure(
            text=f"Listo para procesar: {self.ruta_pendiente.name}"
        )

    def procesar(self):
        if self.ruta_pendiente:
            ruta = self.ruta_pendiente
            obra = self.referencia.get().strip() or None
            self.app.run_task(
                "Procesando PDF…",
                lambda: self.service.procesar(
                    ruta, obra_clave=obra
                ),
                self.completado,
            )
        elif self.actual:
            fila = dict(self.actual)
            self.app.run_task(
                "Procesando documento…",
                lambda: self.service.procesar(
                    fila["ruta_local"],
                    nombre=fila["nombre"],
                    fuente=fila["fuente"],
                    obra_clave=fila.get("obra_clave"),
                    contexto=fila.get("contexto"),
                    archivo_origen=fila.get("archivo_origen"),
                    miembro_archivo=fila.get("miembro_archivo"),
                ),
                self.completado,
            )
        else:
            self.mensaje(
                "Cargue un PDF o seleccione un documento para procesar."
            )

    def procesar_descarga(self, payload):
        ruta = Path(payload["descarga"]["ruta_local"])
        if ruta.suffix.lower() not in (".pdf", ".zip", ".rar"):
            return self.app.notice("La descarga se conservó. Se admiten PDF, ZIP y RAR.")

        self.app.tabs.set("Procesar PDFs")
        self.app.run_task(
            "Procesando documento descargado…",
            lambda: self.service.procesar_descarga(payload),
            self.completado,
        )

    def reprocesar(self):
        self.procesar()

    def vaciar_filtros(self):
        for entrada in (
            self.busqueda,
            self.filtro_obra,
            self.filtro_anio,
            self.filtro_lugar,
        ):
            entrada.delete(0, "end")

    def completado(self, resultado):
        self.ruta_pendiente = None
        self.referencia.delete(0, "end")
        self.actual = resultado
        self.vista.set("Hallazgos sin incorporar")
        self.ambito.set("Documento seleccionado")
        self.vaciar_filtros()
        self.actualizar()

        if self.actual:
            self.tabla.see(self.actual["documento_id"])
            self.seleccionar()

        self.app.tabs.set("Procesar PDFs")
        if lote := resultado.get("lote"):
            self.app.status.configure(text_color=DISPONIBLE, text=(
                f"{lote['archivo']} · {lote['documentos_procesados']} PDFs procesados · "
                f"{lote['candidatos']} hallazgos."
            ))
            if lote["avisos"]:
                self.app.notice("El archivo se procesó con avisos:\n" + "\n".join(lote["avisos"][:5]))
            return
        self.app.status.configure(
            text_color=DISPONIBLE, text=(
                f"Procesado: {resultado['nombre']} · "
                f"{resultado['candidatos']} hallazgos."
            )
        )

    def seleccionar(self, _evento=None):
        seleccion = self.tabla.selection()
        if not seleccion:
            return

        self.actual = next(
            (
                fila for fila in self.filas
                if fila["documento_id"] == seleccion[0]
            ),
            None,
        )
        if not self.actual:
            return

        self.ruta_pendiente = None
        self.resumen.configure(
            text=(
                f"{self.actual['nombre']} · "
                f"{self.actual['candidatos']} hallazgos"
            )
        )
        self.actualizar_resultados()

    def actualizar_resultados(self):
        if (
            self.ambito.get() == "Documento seleccionado"
            and not self.actual
        ):
            self.consulta.cancelar()
            self.consulta.guardadas = self.vista.get() == "Datos guardados"
            self.consulta.filas = {}
            self.resultados.delete(*self.resultados.get_children())
            self.contar()
            self.mostrar_vacio(
                "Pulsa Procesar para leer el PDF cargado." if self.ruta_pendiente
                else "Selecciona un documento para ver sus datos."
            )
            return

        doc = None
        if (
            self.actual
            and self.ambito.get() == "Documento seleccionado"
        ):
            doc = self.actual["documento_id"]

        filtros = {
            'termino': self.busqueda.get().strip(),
            'obra': self.filtro_obra.get().strip(),
            'anio': self.filtro_anio.get().strip(),
            'lugar': self.filtro_lugar.get().strip(),
        }
        try:
            filas = self.consulta.actualizar(
                guardadas=self.vista.get() == "Datos guardados",
                documento_id=doc,
                **filtros,
            )
        except ValueError as error:
            self.mensaje(str(error))
            return
        except Exception as error:
            self.app.show_error(error)
            return

        self.resultados.delete(*self.resultados.get_children())
        self.estado_vacio.place_forget()

        for fila in filas:
            self.resultados.insert(
                "",
                "end",
                iid=fila["id"],
                values=(
                    "Guardado" if self.consulta.guardadas else "☐",
                    fila["descripcion"],
                    fila.get("unidad") or "Sin extraer",
                    fila.get("precio_unitario_texto") or "",
                    (fila.get("monto_texto") or "") if not fila.get("precio_unitario_texto") else "",
                    fila.get("moneda") or "Sin registrar",
                    fila.get("fuente") or "Sin registrar",
                    fila.get("obra")
                    or fila.get("obra_clave")
                    or "Sin registrar",
                    fila.get("anio") or "Sin registrar",
                    fila.get("lugar") or "Sin registrar",
                ),
            )

        self.contar()
        if not filas:
            if doc and not self.actual["candidatos"]:
                texto = "No se encontraron datos en este documento."
            elif any(filtros.values()):
                texto = "Sin coincidencias. Ajusta los filtros o pulsa Limpiar."
            elif self.consulta.guardadas:
                texto = "Sin datos guardados. Marca y guarda hallazgos para consultarlos aquí."
            elif doc:
                texto = "No hay hallazgos pendientes. Consulta Datos guardados."
            else:
                texto = "Sin hallazgos pendientes. Carga un PDF o revisa Datos guardados."
            self.mostrar_vacio(texto)

    def mostrar_vacio(self, texto):
        self.estado_vacio.configure(text=texto)
        self.estado_vacio.place(relx=.5, rely=.5, anchor="center")

    def enviar_estimador(self):
        if getattr(self.app, "busy", False):
            return
        seleccion = self.resultados.selection()
        fila = self.consulta.filas.get(seleccion[0]) if seleccion else None
        if self.vista.get() != "Datos guardados" or not fila:
            self.app.notice("Selecciona una partida de Datos guardados.")
            return
        estimador = self.app.estimacion_partidas
        if estimador.agregar(fila):
            self.app.tabs.set("Estimador")
            estimador.master.select(estimador)

    def actualizar_acciones(self):
        ocupado = self.app.busy
        pendientes = not self.consulta.guardadas
        marcados = bool(self.consulta.marcados)
        hay_filas = bool(self.consulta.filas)

        if pendientes:
            self.boton_estimar.pack_forget()
            self.acciones_hallazgos.pack(side="left")
        else:
            self.acciones_hallazgos.pack_forget()
            self.boton_estimar.pack(side="left", padx=4)

        def estado(disponible):
            return "normal" if disponible and not ocupado else "disabled"

        self.boton_procesar.configure(state=estado(self.ruta_pendiente or self.actual))
        self.boton_todos.configure(state=estado(pendientes and hay_filas))
        self.boton_guardar.configure(state=estado(pendientes and marcados))
        self.boton_cancelar.configure(state=estado(pendientes and marcados))

        seleccion = self.resultados.selection()
        fila = self.consulta.filas.get(seleccion[0]) if seleccion else None
        puede_estimar = False
        ayuda = ""
        if self.consulta.guardadas and hay_filas:
            ayuda = "Selecciona una partida guardada para estimar."
            if fila:
                try:
                    precio_partida(fila)
                except ValueError as error:
                    ayuda = str(error)
                else:
                    puede_estimar = True
                    ayuda = "Partida seleccionada. Pulsa Enviar al estimador."
        elif pendientes and hay_filas and not marcados:
            ayuda = "Marca las filas que quieres guardar en la columna Elegir."

        self.boton_estimar.configure(state=estado(puede_estimar))
        self.ayuda_acciones.configure(text=ayuda)

    def contar(self):
        self.actualizar_acciones()
        estado = (
            "Datos guardados"
            if self.consulta.guardadas
            else f"Seleccionados: {len(self.consulta.marcados)}"
        )
        self.mensaje(
            f"Resultados: {len(self.consulta.filas)} · {estado}"
        )

    def alternar_marca(self, evento):
        if (
            getattr(self.app, "busy", False)
            or self.consulta.guardadas
        ):
            return

        if self.resultados.identify_region(
            evento.x, evento.y
        ) != "cell":
            return

        if self.resultados.identify_column(evento.x) != "#1":
            return

        clave = self.resultados.identify_row(evento.y)
        if not clave:
            return

        self.consulta.alternar(clave)
        self.resultados.set(
            clave,
            "elegir",
            "☑" if clave in self.consulta.marcados else "☐",
        )
        self.resultados.selection_set(clave)
        self.contar()
        return "break"

    def seleccionar_todos(self):
        if (
            getattr(self.app, "busy", False)
            or self.consulta.guardadas
        ):
            return

        self.consulta.seleccionar_todos()
        for clave in self.consulta.marcados:
            self.resultados.set(clave, "elegir", "☑")
        self.contar()

    def cancelar(self):
        if (
            getattr(self.app, "busy", False)
            or self.consulta.guardadas
        ):
            return

        self.consulta.cancelar()
        for clave in self.consulta.filas:
            self.resultados.set(clave, "elegir", "☐")

        self.contar()
        self.mensaje(
            "Selección cancelada. No se guardaron datos adicionales."
        )

    def guardar(self):
        if (
            getattr(self.app, "busy", False)
            or self.consulta.guardadas
        ):
            return

        try:
            nuevos = self.consulta.guardar()
        except Exception as error:
            self.mensaje(str(error))
            return

        self.actualizar_resultados()
        self.mensaje(
            f"{nuevos} datos nuevos guardados. "
            "Consulte Datos guardados."
        )

    def limpiar_busqueda(self):
        self.vaciar_filtros()
        self.actualizar_resultados()

    def resumir_resultado(self, _evento=None):
        self.actualizar_acciones()
        seleccion = self.resultados.selection()
        fila = self.consulta.filas.get(seleccion[0]) if seleccion else None
        if fila:
            fuente = fila.get("fuente") or "Fuente no registrada"
            obra = fila.get("obra") or fila.get("obra_clave") or "Obra no registrada"
            self.resumen.configure(text=f"{fuente} · {obra} · Página {fila['pagina']}")

    def revisar(self):
        self.actualizar_resultados()
        self.resultados.focus_set()

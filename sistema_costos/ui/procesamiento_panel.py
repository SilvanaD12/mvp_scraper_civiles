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
        app.button(barra, "Procesar", self.procesar).pack(
            side="left", padx=4
        )
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
            width=215,
            command=lambda _: self.actualizar_resultados(),
        )
        self.vista.pack(side="left", padx=4)

        self.ambito = ctk.CTkOptionMenu(
            filtros,
            values=["Documento seleccionado", "Todos los documentos"],
            width=200,
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

        self.boton_todos = app.button(
            pie, "Seleccionar visibles", self.seleccionar_todos
        )
        self.boton_todos.pack(side="left", padx=4)

        self.boton_guardar = app.button(
            pie, "Guardar seleccionados", self.guardar
        )
        self.boton_guardar.pack(side="left", padx=4)

        self.boton_cancelar = app.button(
            pie, "Cancelar selección", self.cancelar
        )
        self.boton_cancelar.pack(side="left", padx=4)

        self.contador = ctk.CTkLabel(
            self, text="", anchor="w"
        )
        self.contador.grid(
            row=6, column=0, sticky="ew", padx=5, pady=3
        )

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
        self.resumen.configure(
            text=f"Listo para procesar: {self.ruta_pendiente.name}"
        )
        self.mensaje(
            "Pulse Procesar para leer el PDF y obtener sus resultados."
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
            self.app.status.configure(text=(
                f"{lote['archivo']} · {lote['documentos_procesados']} PDFs procesados · "
                f"{lote['candidatos']} hallazgos."
            ))
            if lote["avisos"]:
                self.app.notice("El archivo se procesó con avisos:\n" + "\n".join(lote["avisos"][:5]))
            return
        self.app.status.configure(
            text=(
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
            self.consulta.filas = {}
            self.resultados.delete(*self.resultados.get_children())
            self.mensaje(
                "Seleccione un documento o elija "
                "Todos los documentos para consultar."
            )
            return

        doc = None
        if (
            self.actual
            and self.ambito.get() == "Documento seleccionado"
        ):
            doc = self.actual["documento_id"]

        try:
            filas = self.consulta.actualizar(
                guardadas=self.vista.get() == "Datos guardados",
                documento_id=doc,
                termino=self.busqueda.get().strip(),
                obra=self.filtro_obra.get().strip(),
                anio=self.filtro_anio.get().strip(),
                lugar=self.filtro_lugar.get().strip(),
            )
        except ValueError as error:
            self.mensaje(str(error))
            return
        except Exception as error:
            self.app.show_error(error)
            return

        self.resultados.delete(*self.resultados.get_children())

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
            self.mensaje(
                "No hay resultados para esta vista y estos filtros. "
                "Pruebe Limpiar o cambie la vista de resultados."
            )

    def contar(self):
        deshabilitar = (
            self.consulta.guardadas
            or getattr(self.app, "busy", False)
        )
        for boton in (
            self.boton_todos,
            self.boton_guardar,
            self.boton_cancelar,
        ):
            boton.configure(
                state="disabled" if deshabilitar else "normal"
            )

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
        seleccion = self.resultados.selection()
        fila = self.consulta.filas.get(seleccion[0]) if seleccion else None
        if fila:
            fuente = fila.get("fuente") or "Fuente no registrada"
            obra = fila.get("obra") or fila.get("obra_clave") or "Obra no registrada"
            self.resumen.configure(text=f"{fuente} · {obra} · Página {fila['pagina']}")

    def revisar(self):
        self.actualizar_resultados()
        self.resultados.focus_set()

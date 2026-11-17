"""Vista de estimación preliminar por partidas seleccionadas."""

import webbrowser
from tkinter import ttk

import customtkinter as ctk

from costeo_mvp.partidas import (
    precio_partida,
    subtotales_por_moneda,
)
from sistema_costos.database.candidatos_repository import CandidatosRepository
from sistema_costos.database.partidas_seleccionadas_repository import (
    PartidasSeleccionadasRepository,
)
from sistema_costos.services.revision_candidatos import RevisionCandidatosService

from .dialogo_metrado import DialogoMetrado
from .tema import PANEL, TEXTO


class EstimacionPartidas(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=12)
        from .references_app import table

        self.app = app
        self.partidas = {}

        ruta = app.settings.database_path
        self.revision = RevisionCandidatosService(
            CandidatosRepository(ruta),
            PartidasSeleccionadasRepository(ruta),
        )

        ttk.Label(
            self,
            text="Partidas de la estimación",
            style="Section.TLabel",
        ).pack(anchor="w", pady=(0, 4))

        ttk.Label(
            self,
            style="Muted.TLabel",
            text=(
                "En Procesar PDFs → Datos guardados, elige una partida "
                "y pulsa Enviar al estimador."
            ),
            wraplength=750,
        ).pack(anchor="w", pady=(0, 8))

        frame, self.tabla = table(
            self,
            [
                ("descripcion", "Partida", 235),
                ("unidad", "Unidad", 65),
                ("metrado", "Metrado", 80),
                ("precio", "Precio unitario", 105),
                ("parcial", "Parcial", 105),
                ("moneda", "Moneda", 70),
                ("documento", "Documento", 200),
                ("pagina", "Página", 65),
                ("fuente", "Fuente", 110),
            ],
        )
        frame.pack(fill="both", expand=True)

        self.boton_quitar = ttk.Button(
            self,
            text="Quitar partida",
            command=self.quitar,
            state="disabled",
        )
        self.boton_quitar.pack(anchor="w", pady=6)
        self.tabla.bind("<<TreeviewSelect>>", self.actualizar_acciones)

        self.total = ttk.Label(
            self,
            text="Sin partidas en el cálculo.",
            style="Total.TLabel",
        )
        self.total.pack(anchor="w")

        ttk.Label(
            self,
            text=(
                "Costo directo preliminar de las partidas incluidas. "
                "Requiere revisión de Ingeniería."
            ),
            wraplength=750,
        ).pack(anchor="w", pady=(4, 0))

        detalle = ttk.Frame(self, padding=10)
        detalle.pack(fill="x", pady=(10, 0))
        detalle.columnconfigure(0, weight=1)

        ttk.Label(
            detalle,
            text="Detalle de la partida",
            style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.boton_abrir_pdf = ttk.Button(
            detalle,
            text="Abrir PDF",
            command=self.abrir_pdf_resultado,
            state="disabled",
        )
        self.boton_abrir_pdf.grid(
            row=0, column=1, sticky="e", pady=(0, 6),
        )

        self.detalle_texto = ctk.CTkTextbox(
            detalle,
            height=140,
            wrap="word",
            fg_color=PANEL,
            text_color=TEXTO,
        )
        self.detalle_texto.grid(
            row=1, column=0, columnspan=2, sticky="ew",
        )
        self.actualizar_detalle()

    def agregar(self, fila):
        try:
            precio = precio_partida(fila)
        except ValueError as error:
            self.app.notice(str(error))
            return False

        anterior = self.partidas.get(fila["id"])
        metrado_inicial = str(anterior["metrado"]) if anterior else ""

        dialogo = DialogoMetrado(
            self.app,
            fila,
            precio,
            metrado_inicial=metrado_inicial,
        )
        self.app.wait_window(dialogo)

        if dialogo.partida is None:
            return False

        self.partidas[fila["id"]] = dialogo.partida
        self.actualizar()
        self.tabla.selection_set(fila["id"])
        self.tabla.see(fila["id"])
        self.actualizar_acciones()
        return True

    def actualizar_acciones(self, _event=None):
        self.boton_quitar.configure(
            state="normal" if self.tabla.selection() else "disabled",
        )
        self.actualizar_detalle()

    def quitar(self):
        seleccion = self.tabla.selection()
        if seleccion:
            self.partidas.pop(seleccion[0], None)
            self.actualizar()

    def actualizar(self):
        self.tabla.delete(*self.tabla.get_children())

        for identificador, fila in self.partidas.items():
            self.tabla.insert(
                "",
                "end",
                iid=identificador,
                values=(
                    fila["descripcion"],
                    fila["unidad"],
                    fila["metrado"],
                    fila["precio"],
                    fila["parcial"],
                    fila["moneda"],
                    fila["documento_nombre"],
                    fila["pagina"],
                    fila["fuente"],
                ),
            )

        self.actualizar_acciones()
        subtotales = subtotales_por_moneda(self.partidas.values())
        texto = "  ·  ".join(
            f"{moneda} {importe:,.2f}"
            for moneda, importe in sorted(subtotales.items())
        )
        self.total.configure(
            text=(
                f"Subtotal por moneda: {texto}"
                if texto
                else "Sin partidas en el cálculo."
            ),
        )

    def actualizar_detalle(self):
        seleccion = self.tabla.selection()
        fila = self.partidas.get(seleccion[0]) if seleccion else None
        texto = (
            "Selecciona una partida de la estimación "
            "para consultar su fuente."
        )

        if fila:
            descripcion = fila.get("descripcion") or "Sin descripción"
            documento = fila.get("documento_nombre") or "Sin registrar"
            pagina = fila.get("pagina") or "Sin registrar"
            fuente = fila.get("fuente") or "Sin registrar"

            texto = (
                f"{descripcion}\n\n"
                f"Metrado: {fila['metrado']} {fila['unidad']}    "
                f"Precio unitario: {fila['moneda']} {fila['precio']}\n"
                f"Parcial: {fila['moneda']} {fila['parcial']}\n"
                f"Documento: {documento}\n"
                f"Página de referencia: {pagina}    Fuente: {fuente}"
            )

        self.detalle_texto.configure(state="normal")
        self.detalle_texto.delete("1.0", "end")
        self.detalle_texto.insert("1.0", texto)
        self.detalle_texto.configure(state="disabled")
        self.boton_abrir_pdf.configure(
            state="normal" if fila else "disabled",
        )

    def abrir_pdf_resultado(self):
        seleccion = self.tabla.selection()
        fila = self.partidas.get(seleccion[0]) if seleccion else None

        if not fila:
            self.app.notice("Selecciona una partida de la estimación.")
            return

        try:
            ruta = self.revision.obtener_ruta_pdf(fila["id"])
            abierto = webbrowser.open(ruta.as_uri())
            if not abierto:
                self.app.notice(
                    "No se pudo abrir el PDF. "
                    "Comprueba tu navegador predeterminado."
                )
        except (ValueError, FileNotFoundError, OSError) as error:
            self.app.notice(str(error))
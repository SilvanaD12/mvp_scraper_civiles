"""Vista de estimación preliminar por partidas seleccionadas."""

from tkinter import simpledialog, ttk

from costeo_mvp.partidas import calcular_partida, precio_partida, subtotales_por_moneda


class EstimacionPartidas(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=12)
        from .references_app import table

        self.app = app
        self.partidas = {}
        ttk.Label(self, text="Partidas de la estimación", style="Section.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(
            self, style="Muted.TLabel",
            text="En Procesar PDFs → Datos guardados, elige una partida y pulsa Enviar al estimador.",
            wraplength=750,
        ).pack(anchor="w", pady=(0, 8))
        frame, self.tabla = table(self, [
            ("descripcion", "Partida", 235),
            ("unidad", "Unidad", 65),
            ("metrado", "Metrado", 80),
            ("precio", "Precio unitario", 105),
            ("parcial", "Parcial", 105),
            ("moneda", "Moneda", 70),
            ("documento", "Documento", 200),
            ("pagina", "Página", 65),
            ("fuente", "Fuente", 110),
        ])
        frame.pack(fill="both", expand=True)
        self.boton_quitar = ttk.Button(self, text="Quitar partida", command=self.quitar, state="disabled")
        self.boton_quitar.pack(anchor="w", pady=6)
        self.tabla.bind("<<TreeviewSelect>>", self.actualizar_acciones)
        self.total = ttk.Label(self, text="Sin partidas en el cálculo.", style="Total.TLabel")
        self.total.pack(anchor="w")
        ttk.Label(
            self, text="Costo directo preliminar de las partidas incluidas. "
            "Requiere revisión de Ingeniería.", wraplength=750,
        ).pack(anchor="w", pady=(4, 0))

    def agregar(self, fila):
        try:
            precio = precio_partida(fila)
        except ValueError as error:
            self.app.notice(str(error))
            return False

        anterior = self.partidas.get(fila["id"])
        metrado = simpledialog.askstring(
            "Revisar precio e ingresar metrado",
            f"{fila['descripcion']}\n"
            f"{fila['documento_nombre']} · página {fila['pagina']} · {fila['fuente']}\n"
            f"Precio de referencia: {fila['moneda']} {precio} por {fila['unidad']}\n\n"
            "Si ya cotejaste el precio y la unidad en el documento, "
            f"ingresa el metrado del proyecto en {fila['unidad']}.",
            initialvalue=str(anterior["metrado"]) if anterior else "",
            parent=self.app,
        )
        if metrado is None:
            return False
        try:
            partida = calcular_partida(fila, metrado)
        except ValueError as error:
            self.app.notice(str(error))
            return False

        self.partidas[fila["id"]] = partida
        self.actualizar()
        return True

    def actualizar_acciones(self, _event=None):
        self.boton_quitar.configure(state="normal" if self.tabla.selection() else "disabled")

    def quitar(self):
        seleccion = self.tabla.selection()
        if seleccion:
            self.partidas.pop(seleccion[0])
            self.actualizar()

    def actualizar(self):
        self.tabla.delete(*self.tabla.get_children())
        for identificador, fila in self.partidas.items():
            self.tabla.insert("", "end", iid=identificador, values=(
                fila["descripcion"], fila["unidad"], fila["metrado"], fila["precio"],
                fila["parcial"], fila["moneda"], fila["documento_nombre"],
                fila["pagina"], fila["fuente"],
            ))
        self.actualizar_acciones()
        subtotales = subtotales_por_moneda(self.partidas.values())
        texto = "  ·  ".join(f"{moneda} {importe:,.2f}" for moneda, importe in sorted(subtotales.items()))
        self.total.configure(text=f"Subtotal por moneda: {texto}" if texto else "Sin partidas en el cálculo.")

"""Diálogo para revisar una partida e ingresar su metrado."""

import customtkinter as ctk

from costeo_mvp.partidas import calcular_partida

from .tema import PANEL, SECUNDARIO, SUPERFICIE, TEXTO


class DialogoMetrado(ctk.CTkToplevel):
    def __init__(self, app, fila, precio, metrado_inicial=""):
        super().__init__(app)

        self.fila = fila
        self.partida = None

        self.title("Ingresar metrado")
        self.geometry("620x520")
        self.minsize(520, 480)
        self.configure(fg_color=PANEL)
        self.transient(app)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            self,
            text="Revisar partida e ingresar metrado",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXTO,
            anchor="w",
        ).grid(
            row=0, column=0, sticky="ew",
            padx=24, pady=(22, 12),
        )

        informacion = ctk.CTkTextbox(
            self,
            height=150,
            wrap="word",
            fg_color=SUPERFICIE,
            text_color=TEXTO,
        )
        informacion.grid(
            row=1, column=0, sticky="ew", padx=24, pady=(0, 14),
        )
        informacion.insert(
            "1.0",
            f"{fila['descripcion']}\n\n"
            f"Precio unitario: {fila['moneda']} {precio} "
            f"por {fila['unidad']}\n"
            f"Documento: {fila['documento_nombre']}\n"
            f"Página de referencia: {fila['pagina']}",
        )
        informacion.configure(state="disabled")

        ctk.CTkLabel(
            self,
            text=f"Metrado del proyecto · Unidad: {fila['unidad']}",
            text_color=TEXTO,
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=24)

        self.entrada = ctk.CTkEntry(
            self,
            height=38,
            placeholder_text="Ingresa una cantidad mayor que cero",
            fg_color=SUPERFICIE,
            text_color=TEXTO,
        )
        self.entrada.grid(
            row=3, column=0, sticky="ew",
            padx=24, pady=(6, 0),
        )
        self.entrada.insert(0, metrado_inicial)

        self.error = ctk.CTkLabel(
            self,
            text="",
            text_color="#FFB4AB",
            anchor="w",
            justify="left",
            wraplength=470,
        )
        self.error.grid(
            row=4, column=0, sticky="new",
            padx=24, pady=(6, 0),
        )

        ctk.CTkLabel(
            self,
            text="Comprueba el precio y la unidad en el PDF antes de agregar.",
            text_color=SECUNDARIO,
            anchor="w",
            justify="left",
            wraplength=470,
        ).grid(
            row=5, column=0, sticky="ew",
            padx=24, pady=(8, 12),
        )

        acciones = ctk.CTkFrame(self, fg_color="transparent")
        acciones.grid(
            row=6, column=0, sticky="e",
            padx=24, pady=(0, 22),
        )

        app.button(
            acciones,
            "Cancelar",
            self.destroy,
            registrar=False,
        ).pack(side="left", padx=(0, 8))

        app.button(
            acciones,
            "Agregar al cálculo",
            self.confirmar,
            variante="principal",
            registrar=False,
        ).pack(side="left")

        self.entrada.bind("<Return>", self.confirmar)
        self.bind("<Escape>", lambda _evento: self.destroy())

        self.wait_visibility()
        self.grab_set()
        self.entrada.focus_set()
        self.entrada.select_range(0, "end")

    def confirmar(self, _evento=None):
        try:
            partida = calcular_partida(
                self.fila,
                self.entrada.get(),
            )
        except ValueError as error:
            self.error.configure(text=str(error))
            self.entrada.focus_set()
            return

        self.partida = partida
        self.destroy()
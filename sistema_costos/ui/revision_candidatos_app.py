"""Selección de datos extraídos para incorporarlos a la consulta."""

import os
import subprocess
import sys
import tkinter as tk

from tkinter import messagebox, ttk

import customtkinter as ctk

from sistema_costos.config.settings import get_settings
from sistema_costos.database.candidatos_repository import (
    CandidatosRepository,
)
from sistema_costos.database.partidas_seleccionadas_repository import (
    PartidasSeleccionadasRepository,
)
from sistema_costos.services.revision_candidatos import (
    RevisionCandidatosService,
)


class RevisionCandidatosApp(ctk.CTk):
    def __init__(
        self,
        servicio: RevisionCandidatosService,
        ruta_base: str,
    ) -> None:
        super().__init__()

        self.servicio = servicio
        self.candidatos: dict[str, dict] = {}
        self.marcados: set[str] = set()

        self.title("Ceniteg | Selección de datos extraídos")
        self.geometry("1200x800")
        self.minsize(950, 650)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._crear_encabezado(ruta_base)
        self._crear_controles()
        self._crear_tabla()
        self._crear_detalle()
        self._crear_botones()

        self.estado_pantalla = ctk.CTkLabel(
            self,
            text="",
            anchor="w",
            wraplength=900,
        )
        self.estado_pantalla.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 10),
        )

        self.actualizar()

    def _crear_encabezado(self, ruta_base: str) -> None:
        marco = ctk.CTkFrame(self)
        marco.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=20,
            pady=15,
        )

        ctk.CTkLabel(
            marco,
            text="Selección de datos extraídos",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(12, 5))

        ctk.CTkLabel(
            marco,
            text=(
                "Consulta la evidencia y marca las casillas "
                "de los datos que quieres incorporar. "
                "Luego pulsa Guardar seleccionados."
            ),
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 5))

        ctk.CTkLabel(
            marco,
            text=f"Base de datos: {ruta_base}",
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=15, pady=(0, 12))

    def _crear_controles(self) -> None:
        marco = ctk.CTkFrame(self)
        marco.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 10),
        )

        ctk.CTkLabel(
            marco,
            text="Mostrar:",
        ).pack(side="left", padx=12, pady=10)

        self.vista = ctk.CTkOptionMenu(
            marco,
            values=[
                "Hallazgos sin incorporar",
                "Datos guardados",
            ],
            command=lambda _: self.actualizar(),
            width=210,
        )
        self.vista.set("Hallazgos sin incorporar")
        self.vista.pack(side="left", pady=10)

        ctk.CTkButton(
            marco,
            text="Actualizar",
            command=self.actualizar,
        ).pack(side="left", padx=10, pady=10)

        self.boton_todos = ctk.CTkButton(
            marco,
            text="Seleccionar todos",
            command=self._seleccionar_todos,
        )
        self.boton_todos.pack(
            side="left",
            padx=(0, 10),
            pady=10,
        )

    def _crear_tabla(self) -> None:
        marco = ctk.CTkFrame(self)
        marco.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=20,
            pady=(0, 10),
        )
        marco.grid_columnconfigure(0, weight=1)
        marco.grid_rowconfigure(0, weight=1)

        estilo = ttk.Style(self)
        estilo.theme_use("clam")

        estilo.configure(
            "Ceniteg.Treeview",
            background="#242424",
            foreground="white",
            fieldbackground="#242424",
            rowheight=30,
        )
        estilo.configure(
            "Ceniteg.Treeview.Heading",
            background="#343434",
            foreground="white",
        )
        estilo.map(
            "Ceniteg.Treeview",
            background=[("selected", "#1f538d")],
        )

        columnas = (
            "seleccion",
            "documento",
            "pagina",
            "descripcion",
            "unidad",
            "precio",
        )

        self.tabla = ttk.Treeview(
            marco,
            columns=columnas,
            show="headings",
            selectmode="browse",
            style="Ceniteg.Treeview",
        )

        configuracion = (
            ("seleccion", "Elegir", 90),
            ("documento", "Documento", 220),
            ("pagina", "Página", 65),
            ("descripcion", "Descripción", 340),
            ("unidad", "Unidad", 70),
            ("precio", "Precio original", 130),
        )

        for columna, titulo, ancho in configuracion:
            self.tabla.heading(columna, text=titulo)
            self.tabla.column(
                columna,
                width=ancho,
                minwidth=60,
            )

        self.tabla.column(
            "seleccion",
            stretch=False,
            anchor="center",
        )

        self.tabla.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(10, 0),
            pady=(10, 0),
        )

        vertical = ttk.Scrollbar(
            marco,
            orient="vertical",
            command=self.tabla.yview,
        )
        vertical.grid(
            row=0,
            column=1,
            sticky="ns",
            padx=(0, 10),
            pady=(10, 0),
        )

        horizontal = ttk.Scrollbar(
            marco,
            orient="horizontal",
            command=self.tabla.xview,
        )
        horizontal.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(10, 0),
            pady=(0, 10),
        )

        self.tabla.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )

        self.tabla.bind(
            "<<TreeviewSelect>>",
            self._mostrar_detalle,
        )
        self.tabla.bind(
            "<Button-1>",
            self._alternar_marca,
        )

    def _crear_detalle(self) -> None:
        marco = ctk.CTkFrame(self)
        marco.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 10),
        )

        ctk.CTkLabel(
            marco,
            text="Dato seleccionado y evidencia original",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(10, 5))

        self.detalle = ctk.CTkTextbox(
            marco,
            height=190,
            wrap="word",
        )
        self.detalle.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(0, 12),
        )

    def _crear_botones(self) -> None:
        marco = ctk.CTkFrame(self)
        marco.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 10),
        )

        ctk.CTkButton(
            marco,
            text="Abrir PDF original",
            command=self._abrir_pdf,
        ).pack(side="left", padx=12, pady=12)

        self.boton_guardar = ctk.CTkButton(
            marco,
            text="Guardar seleccionados",
            command=self._guardar,
        )
        self.boton_guardar.pack(
            side="left",
            padx=(0, 12),
            pady=12,
        )

        self.boton_cancelar = ctk.CTkButton(
            marco,
            text="Cancelar",
            command=self._cancelar,
        )
        self.boton_cancelar.pack(
            side="left",
            padx=(0, 12),
            pady=12,
        )

    def _viendo_guardados(self) -> bool:
        return self.vista.get() == "Datos guardados"

    def actualizar(self) -> bool:
        try:
            filas = self.servicio.listar(
                guardadas=self._viendo_guardados()
            )
        except (ValueError, RuntimeError) as error:
            messagebox.showerror(
                "Error al consultar",
                str(error),
                parent=self,
            )
            return False

        self.marcados.clear()

        for elemento in self.tabla.get_children():
            self.tabla.delete(elemento)

        self.candidatos = {
            fila["id"]: fila
            for fila in filas
        }

        for fila in filas:
            self.tabla.insert(
                "",
                "end",
                iid=fila["id"],
                values=(
                    (
                        "Guardado"
                        if self._viendo_guardados()
                        else "☐"
                    ),
                    fila["documento_nombre"],
                    fila["pagina"],
                    fila["descripcion"],
                    fila["unidad"] or "Sin extraer",
                    fila["precio_unitario_texto"] or "Sin extraer",
                ),
            )

        estado = (
            "disabled"
            if self._viendo_guardados()
            else "normal"
        )

        for boton in (
            self.boton_todos,
            self.boton_guardar,
            self.boton_cancelar,
        ):
            boton.configure(state=estado)

        self._escribir_detalle(
            "Selecciona una fila para consultar su evidencia."
        )
        self._actualizar_contador()

        return True

    def _actualizar_contador(self) -> None:
        if self._viendo_guardados():
            texto = (
                f"Datos guardados: {len(self.candidatos)}."
            )
        elif self.candidatos:
            texto = (
                f"Hallazgos: {len(self.candidatos)}"
                f" | Seleccionados: {len(self.marcados)}"
            )
        else:
            texto = (
                "No hay hallazgos sin incorporar. "
                "Se mostrarán cuando se registren "
                "resultados del extractor."
            )

        self.estado_pantalla.configure(text=texto)

    def _alternar_marca(self, evento):
        if self._viendo_guardados():
            return

        region = self.tabla.identify_region(
            evento.x,
            evento.y,
        )

        if region != "cell":
            return

        if self.tabla.identify_column(evento.x) != "#1":
            return

        fila_id = self.tabla.identify_row(evento.y)

        if not fila_id:
            return

        self.tabla.selection_set(fila_id)
        self.tabla.focus(fila_id)

        if fila_id in self.marcados:
            self.marcados.remove(fila_id)
        else:
            self.marcados.add(fila_id)

        self.tabla.set(
            fila_id,
            "seleccion",
            "☑" if fila_id in self.marcados else "☐",
        )

        self._actualizar_contador()
        self._mostrar_detalle()

        return "break"

    def _seleccionar_todos(self) -> None:
        if self._viendo_guardados():
            return

        self.marcados = set(self.candidatos)

        for fila_id in self.candidatos:
            self.tabla.set(
                fila_id,
                "seleccion",
                "☑",
            )

        self._actualizar_contador()

    def _cancelar(self) -> None:
        self.marcados.clear()

        for fila_id in self.candidatos:
            self.tabla.set(
                fila_id,
                "seleccion",
                "☐",
            )

        seleccion = self.tabla.selection()

        if seleccion:
            self.tabla.selection_remove(*seleccion)

        self._escribir_detalle(
            "Selección cancelada. Puedes elegir otros datos."
        )
        self.estado_pantalla.configure(
            text=(
                "Selección cancelada. "
                "No se guardó ningún cambio."
            )
        )

    def _guardar(self) -> None:
        if self._viendo_guardados():
            return

        try:
            nuevos = self.servicio.guardar_seleccion(
                sorted(self.marcados)
            )
        except (ValueError, RuntimeError) as error:
            messagebox.showerror(
                "No se pudo guardar",
                str(error),
                parent=self,
            )
            return

        if self.actualizar():
            self.estado_pantalla.configure(
                text=(
                    f"Datos nuevos incorporados: {nuevos}. "
                    "Puedes verlos en Datos guardados."
                )
            )

    def _seleccionado(self) -> str:
        seleccion = self.tabla.selection()

        if not seleccion:
            raise ValueError(
                "Selecciona una fila para consultar el PDF."
            )

        return seleccion[0]

    def _escribir_detalle(self, texto: str) -> None:
        self.detalle.configure(state="normal")
        self.detalle.delete("1.0", tk.END)
        self.detalle.insert("1.0", texto)
        self.detalle.configure(state="disabled")

    def _mostrar_detalle(self, _evento=None) -> None:
        seleccion = self.tabla.selection()

        if not seleccion:
            return

        fila = self.candidatos.get(seleccion[0])

        if fila is None:
            return

        campos = (
            ("Documento", "documento_nombre"),
            ("Fuente", "fuente"),
            ("Obra", "obra_clave"),
            ("Página del PDF", "pagina"),
            ("Descripción", "descripcion"),
            ("Unidad", "unidad"),
            ("Cantidad", "cantidad_texto"),
            ("Precio unitario", "precio_unitario_texto"),
            ("Moneda", "moneda"),
        )

        lineas = []

        for etiqueta, clave in campos:
            valor = fila[clave]

            if valor is None:
                valor = "Sin registrar"

            lineas.append(f"{etiqueta}: {valor}")

        texto = "\n".join(lineas)
        texto += "\n\nEVIDENCIA ORIGINAL\n"
        texto += fila["texto_evidencia"]

        self._escribir_detalle(texto)

    def _abrir_pdf(self) -> None:
        try:
            ruta = self.servicio.obtener_ruta_pdf(
                self._seleccionado()
            )

            if os.name == "nt":
                os.startfile(str(ruta))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(ruta)])
            else:
                subprocess.Popen(["xdg-open", str(ruta)])

        except (ValueError, RuntimeError, OSError) as error:
            messagebox.showerror(
                "No se pudo abrir el PDF",
                str(error),
                parent=self,
            )


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    ruta = get_settings().database_path

    candidatos = CandidatosRepository(ruta)
    seleccionados = PartidasSeleccionadasRepository(ruta)

    servicio = RevisionCandidatosService(
        candidatos,
        seleccionados,
    )

    app = RevisionCandidatosApp(
        servicio=servicio,
        ruta_base=str(ruta),
    )
    app.mainloop()


if __name__ == "__main__":
    main()
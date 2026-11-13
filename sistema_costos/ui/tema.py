"""Paleta de la aplicación y estilos compartidos con el estimador."""

import sys
from tkinter import ttk

FONDO = "#101824"
PANEL = "#172233"
SUPERFICIE = "#1D2B40"
BORDE = "#30425A"
TEXTO = "#F2F6FC"
SECUNDARIO = "#AFBFD3"
ACENTO = "#83C7FF"
ACCION = "#245DB5"
ACCION_HOVER = "#2E70D0"
FUENTE = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"


def aplicar_tema(ventana):
    estilo = ttk.Style(ventana)
    estilo.theme_use("clam")
    estilo.configure(".", font=(FUENTE, 10), background=PANEL, foreground=TEXTO,
                     bordercolor=BORDE, lightcolor=PANEL, darkcolor=PANEL, focuscolor=ACENTO)
    estilo.configure("TLabel", background=PANEL, foreground=TEXTO)
    estilo.configure("Treeview", background=FONDO, fieldbackground=FONDO, foreground=TEXTO,
                     rowheight=32, borderwidth=0, relief="flat")
    estilo.configure("Treeview.Heading", background=SUPERFICIE, foreground=TEXTO,
                     font=(FUENTE, 10, "bold"), padding=(8, 9), relief="flat")
    estilo.map("Treeview", background=[("selected", ACCION)], foreground=[("selected", TEXTO)])
    estilo.map("Treeview.Heading", background=[("active", BORDE)], foreground=[("active", TEXTO)])
    for orientacion in ("Horizontal", "Vertical"):
        estilo.configure(f"{orientacion}.TScrollbar", background=BORDE, troughcolor=FONDO,
                         arrowcolor=SECUNDARIO, borderwidth=0, arrowsize=12)
        estilo.map(f"{orientacion}.TScrollbar", background=[("active", "#526B89")])
    estilo.configure("TNotebook", borderwidth=0, tabmargins=(0, 0, 0, 5))
    estilo.configure("TNotebook.Tab", background=SUPERFICIE, foreground=SECUNDARIO,
                     padding=(15, 8), borderwidth=0)
    estilo.map("TNotebook.Tab", background=[("selected", ACCION), ("active", BORDE)],
               foreground=[("selected", TEXTO), ("active", TEXTO)])
    estilo.configure("TButton", padding=(10, 6), background=SUPERFICIE)
    estilo.configure("Primary.TButton", background=ACCION)
    for nombre in ("TButton", "Primary.TButton"):
        estilo.map(nombre, background=[("disabled", PANEL), ("pressed", BORDE), ("active", ACCION_HOVER)],
                   foreground=[("disabled", SECUNDARIO)])
    estilo.configure("TEntry", fieldbackground=FONDO, insertcolor=TEXTO, padding=(8, 5))
    estilo.configure("TCombobox", fieldbackground=FONDO, background=SUPERFICIE,
                     arrowcolor=ACENTO, padding=(8, 5))
    estilo.map("TCombobox", fieldbackground=[("readonly", FONDO)],
               selectbackground=[("readonly", FONDO)], selectforeground=[("readonly", TEXTO)])
    estilo.configure("Total.TLabel", foreground=ACENTO, font=(FUENTE, 30, "bold"))
    estilo.configure("Muted.TLabel", foreground=SECUNDARIO)
    ventana.option_add("*TCombobox*Listbox.background", SUPERFICIE)
    ventana.option_add("*TCombobox*Listbox.foreground", TEXTO)
    ventana.option_add("*TCombobox*Listbox.selectBackground", ACCION)


def estilo_texto():
    return dict(bg=FONDO, fg=TEXTO, relief="flat", borderwidth=0,
                padx=12, pady=10, font=(FUENTE, 10), selectbackground=ACCION)

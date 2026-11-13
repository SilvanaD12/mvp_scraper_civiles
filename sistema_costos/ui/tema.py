"""Paleta de la aplicación y estilos compartidos con el estimador."""

import sys
from tkinter import ttk

FONDO = "#F3F5F7"
PANEL = "#FFFFFF"
SUPERFICIE = "#E8EDF2"
BORDE = "#BAC7D3"
TEXTO = "#1B2B3A"
SECUNDARIO = "#4F6173"
ACENTO = "#174A78"
ACCION = "#245B8D"
ACCION_HOVER = "#194A78"
CONTRASTE = "#FFFFFF"
DISPONIBLE = "#276047"
ERROR = "#972C30"
FUENTE = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"


def aplicar_tema(ventana):
    estilo = ttk.Style(ventana)
    estilo.theme_use("clam")
    estilo.configure(".", font=(FUENTE, 10), background=PANEL, foreground=TEXTO,
                     bordercolor=BORDE, lightcolor=PANEL, darkcolor=PANEL, focuscolor=ACENTO)
    estilo.configure("TLabel", background=PANEL, foreground=TEXTO)
    estilo.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXTO,
                     rowheight=30, borderwidth=0, relief="flat")
    estilo.configure("Treeview.Heading", background=SUPERFICIE, foreground=TEXTO,
                     font=(FUENTE, 10, "bold"), padding=(8, 7), relief="flat")
    estilo.map("Treeview", background=[("selected", ACCION)], foreground=[("selected", CONTRASTE)])
    estilo.map("Treeview.Heading", background=[("active", BORDE)], foreground=[("active", TEXTO)])
    for orientacion in ("Horizontal", "Vertical"):
        estilo.configure(f"{orientacion}.TScrollbar", background=BORDE, troughcolor=FONDO,
                         arrowcolor=SECUNDARIO, borderwidth=0, arrowsize=12)
        estilo.map(f"{orientacion}.TScrollbar", background=[("active", "#7A90A6")])
    estilo.configure("TNotebook", borderwidth=0, tabmargins=(0, 0, 0, 5))
    estilo.configure("TNotebook.Tab", background=SUPERFICIE, foreground=SECUNDARIO,
                     padding=(15, 8), borderwidth=0)
    estilo.map("TNotebook.Tab", background=[("selected", ACCION), ("active", BORDE)],
               foreground=[("selected", CONTRASTE), ("active", TEXTO)])
    estilo.configure("TButton", padding=(10, 6), background=SUPERFICIE)
    estilo.configure("Primary.TButton", background=ACCION, foreground=CONTRASTE)
    for nombre in ("TButton", "Primary.TButton"):
        estilo.map(nombre, background=[("disabled", PANEL), ("pressed", BORDE), ("active", ACCION_HOVER)],
                   foreground=[("disabled", SECUNDARIO), ("pressed", TEXTO), ("active", CONTRASTE)])
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
    ventana.option_add("*TCombobox*Listbox.selectForeground", CONTRASTE)


def estilo_texto():
    return dict(bg=FONDO, fg=TEXTO, relief="flat", borderwidth=0,
                padx=12, pady=10, font=(FUENTE, 10), selectbackground=ACCION, selectforeground=CONTRASTE)

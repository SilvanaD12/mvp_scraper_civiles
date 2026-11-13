"""Paleta de la aplicación y estilos compartidos con el estimador."""

import sys
from tkinter import ttk

FONDO = "#222528"
PANEL = "#2A2E31"
SUPERFICIE = "#383E42"
BORDE = "#56616A"
TEXTO = "#E7EAED"
SECUNDARIO = "#BEC7CF"
ACENTO = "#ADD3F1"
ACCION = "#305A7B"
ACCION_HOVER = "#3A678A"
CONTRASTE = "#F2F5F7"
FONDO_DESHABILITADO = "#35393D"
TEXTO_DESHABILITADO = "#B4BCC3"
DISPONIBLE = "#A8CFB4"
ERROR = "#F2B9B9"
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
        estilo.map(f"{orientacion}.TScrollbar", background=[("active", "#73808B")])
    estilo.configure("TNotebook", borderwidth=0, tabmargins=(0, 0, 0, 5))
    estilo.configure("TNotebook.Tab", background=SUPERFICIE, foreground=SECUNDARIO,
                     padding=(15, 8), borderwidth=0)
    estilo.map("TNotebook.Tab", background=[("selected", ACCION), ("active", BORDE)],
               foreground=[("selected", CONTRASTE), ("active", TEXTO)])
    estilo.configure("TButton", padding=(10, 6), background=SUPERFICIE)
    estilo.configure("Primary.TButton", background=ACCION, foreground=CONTRASTE)
    for nombre in ("TButton", "Primary.TButton"):
        estilo.map(nombre, background=[("disabled", FONDO_DESHABILITADO), ("pressed", ACCION), ("active", ACCION_HOVER)],
                   foreground=[("disabled", TEXTO_DESHABILITADO), ("pressed", CONTRASTE), ("active", CONTRASTE)])
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

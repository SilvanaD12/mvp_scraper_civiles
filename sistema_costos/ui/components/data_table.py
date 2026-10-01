"""Tabla ttk reutilizable para visualizar DataFrames."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import customtkinter as ctk
import pandas as pd
from tkinter import ttk


class DataTable(ctk.CTkFrame):
    """Tabla compacta con scroll vertical y horizontal."""

    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(self, show="headings")
        self.vertical_scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.horizontal_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vertical_scroll.set, xscrollcommand=self.horizontal_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vertical_scroll.grid(row=0, column=1, sticky="ns")
        self.horizontal_scroll.grid(row=1, column=0, sticky="ew")

    def set_dataframe(self, frame: pd.DataFrame, columns: Sequence[str] | None = None) -> None:
        visible_columns = list(columns or frame.columns)
        self.tree.delete(*self.tree.get_children())
        self.tree.configure(columns=visible_columns)
        for column in visible_columns:
            self.tree.heading(column, text=column.replace("_", " ").title())
            self.tree.column(column, width=145, minwidth=90, stretch=True, anchor="w")
        for row in frame[visible_columns].itertuples(index=False, name=None):
            values = tuple("" if pd.isna(value) else str(value) for value in row)
            self.tree.insert("", "end", values=values)

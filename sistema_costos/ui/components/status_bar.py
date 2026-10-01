"""Barra de estado y progreso de operaciones."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk


class StatusBar(ctk.CTkFrame):
    def __init__(self, master: Any, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.message = ctk.CTkLabel(self, text="Listo", anchor="w")
        self.message.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.progress = ctk.CTkProgressBar(self, width=150, mode="indeterminate")
        self.progress.grid(row=0, column=1, sticky="e")
        self.progress.grid_remove()

    def set_message(self, value: str) -> None:
        self.message.configure(text=value)

    def set_busy(self, busy: bool) -> None:
        if busy:
            self.progress.grid()
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.grid_remove()

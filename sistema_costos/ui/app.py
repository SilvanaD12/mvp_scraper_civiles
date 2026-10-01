"""Ventana principal de Ceniteg Solutions."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import customtkinter as ctk
import pandas as pd
from tkinter import filedialog, messagebox

from ..config.settings import Settings
from ..database.repository import CostRepository, PriceObservationRecord, ProductRecord, ProviderRecord
from ..scrapers import RawProduct, ScrapeRequest, SodimacScraper
from ..services import ETLService, ExcelExporter
from .components import DataTable, StatusBar

logger = logging.getLogger(__name__)


class CostApp(ctk.CTk):
    """Shell de presentacion; la extraccion corre fuera del hilo de la GUI."""

    def __init__(self, settings: Settings, repository: CostRepository | None = None) -> None:
        super().__init__()
        self.settings = settings
        self.repository = repository or CostRepository(settings.database_path, settings.schema_path)
        self.etl = ETLService()
        self.exporter = ExcelExporter()
        self.normalized = pd.DataFrame()
        self.consolidated = pd.DataFrame()
        self.title(settings.app_name)
        self.geometry("1180x720")
        self.minsize(900, 560)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self._build_layout()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 10))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Extraccion y consolidacion de costos", font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(header, text="Ceniteg Solutions | MVP Fase 1", text_color="#A7B6C8").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )

        controls = ctk.CTkFrame(self)
        controls.grid(row=1, column=0, sticky="ew", padx=24, pady=10)
        controls.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(controls, text="URL de Sodimac").grid(row=0, column=0, padx=(14, 8), pady=14)
        self.url_entry = ctk.CTkEntry(controls, placeholder_text="https://www.sodimac.com.pe/...")
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=14)
        self.extract_button = ctk.CTkButton(controls, text="Extraer", command=self._on_extract)
        self.extract_button.grid(row=0, column=2, padx=8, pady=14)
        self.export_button = ctk.CTkButton(controls, text="Exportar Excel", command=self._on_export, state="disabled")
        self.export_button.grid(row=0, column=3, padx=(8, 14), pady=14)

        self.table = DataTable(self)
        self.table.grid(row=2, column=0, sticky="nsew", padx=24, pady=(10, 12))
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 18))

    def _on_extract(self) -> None:
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("URL requerida", "Ingrese una URL de Sodimac para iniciar la extraccion.")
            return
        self._set_busy(True)
        threading.Thread(target=self._extract_worker, args=(url,), daemon=True).start()

    def _extract_worker(self, url: str) -> None:
        try:
            scraper = SodimacScraper(
                timeout_ms=self.settings.scraper_timeout_ms,
                max_retries=self.settings.scraper_max_retries,
                retry_delay_seconds=self.settings.scraper_retry_delay_seconds,
                headless=self.settings.browser_headless,
            )
            raw_products = list(scraper.scrape(ScrapeRequest(url=url)))
            normalized = self.etl.normalize_products(raw_products)
            consolidated = self.etl.consolidate_prices(normalized)
            self._persist_normalized(raw_products, normalized)
            self.after(0, lambda: self._on_extract_success(normalized, consolidated, len(raw_products)))
        except Exception as exc:
            logger.exception("Error en flujo de extraccion")
            error_message = str(exc)
            self.after(0, lambda: self._on_extract_error(error_message))

    def _persist_normalized(self, raw_products: list[RawProduct], normalized: pd.DataFrame) -> None:
        """Persiste el resultado limpio conservando el valor original observado."""

        if normalized.empty:
            return
        by_key = {(item.name.strip(), str(item.price)): item for item in raw_products}
        provider_id = self.repository.upsert_provider(ProviderRecord(name="Sodimac", website="https://www.sodimac.com.pe"))
        for row in normalized.to_dict(orient="records"):
            category_id = self.repository.upsert_category(str(row.get("category") or ""))
            unit_id = self.repository.upsert_unit(row.get("unit_code"))
            product_id = self.repository.upsert_product(
                ProductRecord(
                    provider_id=provider_id,
                    category_id=category_id,
                    unit_id=unit_id,
                    sku=row.get("sku"),
                    name=str(row["name"]),
                    normalized_name=str(row["normalized_name"]),
                    product_url=row.get("url"),
                )
            )
            original = by_key.get((str(row["name"]), str(row["raw_price"])))
            self.repository.insert_price_observation(
                PriceObservationRecord(
                    product_id=product_id,
                    observed_at=row["observed_at"],
                    price_amount=float(row["price_amount"]),
                    raw_price=str(row.get("raw_price")),
                    currency=str(row.get("currency") or "PEN"),
                    raw_unit=row.get("raw_unit"),
                    normalized_unit_id=unit_id,
                    source_url=original.url if original else row.get("url"),
                    availability=row.get("availability"),
                )
            )

    def _on_extract_success(self, normalized: pd.DataFrame, consolidated: pd.DataFrame, raw_count: int) -> None:
        self.normalized = normalized
        self.consolidated = consolidated
        self.table.set_dataframe(normalized, columns=["name", "price_amount", "currency", "unit_code", "availability"])
        self.export_button.configure(state="normal" if not normalized.empty else "disabled")
        self._set_busy(False)
        self.status_bar.set_message(f"Extraccion completa: {raw_count} encontrados, {len(normalized)} validos")

    def _on_extract_error(self, message: str) -> None:
        self._set_busy(False)
        self.status_bar.set_message("La extraccion finalizo con errores")
        messagebox.showerror("Error de extraccion", message)

    def _on_export(self) -> None:
        if self.normalized.empty:
            return
        default_path = self.settings.exports_dir / "reporte_costos.xlsx"
        destination = filedialog.asksaveasfilename(
            title="Guardar reporte Excel",
            initialdir=str(self.settings.exports_dir),
            initialfile=default_path.name,
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not destination:
            return
        try:
            output = self.exporter.export_report(self.normalized, self.consolidated, Path(destination))
            self.status_bar.set_message(f"Reporte generado: {output.name}")
        except Exception as exc:
            logger.exception("Error al exportar reporte")
            messagebox.showerror("Error de exportacion", str(exc))

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.extract_button.configure(state=state)
        self.status_bar.set_busy(busy)
        if busy:
            self.status_bar.set_message("Extrayendo datos...")

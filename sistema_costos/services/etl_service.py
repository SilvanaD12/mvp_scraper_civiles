"""Limpieza, normalizacion de unidades y estadistica descriptiva."""

from __future__ import annotations

import re
from typing import Sequence

import pandas as pd

from ..scrapers.base_scraper import RawProduct


class ETLError(ValueError):
    """Error de transformacion de datos de costos."""


class ETLService:
    """Transformaciones deterministas para datos de retail y APU."""

    UNIT_ALIASES = {
        "un": "UND",
        "und": "UND",
        "unidad": "UND",
        "u": "UND",
        "kg": "KG",
        "kilogramo": "KG",
        "m": "M",
        "metro": "M",
        "m2": "M2",
        "m²": "M2",
        "metro cuadrado": "M2",
        "m3": "M3",
        "m³": "M3",
        "metro cubico": "M3",
        "l": "L",
        "lt": "L",
        "litro": "L",
    }

    def normalize_products(self, products: Sequence[RawProduct]) -> pd.DataFrame:
        rows = [
            {
                "provider_name": item.provider_name.strip(),
                "name": item.name.strip(),
                "normalized_name": self.normalize_name(item.name),
                "sku": item.sku.strip() if item.sku else None,
                "raw_price": item.price,
                "price_amount": self.parse_price(item.price),
                "currency": (item.currency or "PEN").upper(),
                "raw_unit": item.unit,
                "unit_code": self.normalize_unit(item.unit),
                "url": item.url,
                "category": item.category,
                "availability": item.availability,
                "observed_at": item.extracted_at,
            }
            for item in products
        ]
        columns = [
            "provider_name", "name", "normalized_name", "sku", "raw_price", "price_amount",
            "currency", "raw_unit", "unit_code", "url", "category", "availability", "observed_at",
        ]
        frame = pd.DataFrame(rows, columns=columns)
        if frame.empty:
            return frame
        frame = frame[(frame["name"] != "") & frame["price_amount"].notna()].copy()
        frame["price_amount"] = frame["price_amount"].astype(float)
        return frame.drop_duplicates(subset=["provider_name", "sku", "normalized_name", "price_amount"])

    def consolidate_prices(self, normalized: pd.DataFrame) -> pd.DataFrame:
        if normalized.empty:
            return pd.DataFrame()
        group_columns = ["normalized_name", "unit_code", "currency"]
        return (
            normalized.groupby(group_columns, dropna=False, as_index=False)["price_amount"]
            .agg(
                min_price="min",
                max_price="max",
                average_price="mean",
                median_price="median",
                observations="count",
            )
            .sort_values(["normalized_name", "unit_code"], na_position="last")
            .reset_index(drop=True)
        )

    def normalize_apu_units(self, items: pd.DataFrame, unit_column: str = "unit") -> pd.DataFrame:
        if unit_column not in items.columns:
            raise ETLError(f"No existe la columna de unidad: {unit_column}")
        result = items.copy()
        result["unit_code"] = result[unit_column].map(self.normalize_unit)
        return result

    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = re.sub(r"\s+", " ", value.strip().lower())
        return normalized

    @classmethod
    def normalize_unit(cls, value: object) -> str | None:
        if value is None or pd.isna(value):
            return None
        normalized = str(value).strip().lower()
        return cls.UNIT_ALIASES.get(normalized, normalized.upper()) or None

    @staticmethod
    def parse_price(value: object) -> float | None:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, (int, float)):
            return float(value) if float(value) >= 0 else None
        text = re.sub(r"[^0-9,.-]", "", str(value).strip())
        if not text:
            return None
        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            decimal_part = text.rsplit(",", maxsplit=1)[-1]
            text = text.replace(",", ".") if len(decimal_part) in (1, 2) else text.replace(",", "")
        try:
            parsed = float(text)
        except ValueError:
            return None
        return parsed if parsed >= 0 else None

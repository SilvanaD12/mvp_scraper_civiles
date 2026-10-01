"""Repositorios CRUD parametrizados para el dominio de costos."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .connection import DatabaseConnection, initialize_database


@dataclass(frozen=True, slots=True)
class ProviderRecord:
    name: str
    website: str | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class ProductRecord:
    provider_id: int
    name: str
    normalized_name: str
    sku: str | None = None
    category_id: int | None = None
    unit_id: int | None = None
    product_url: str | None = None


@dataclass(frozen=True, slots=True)
class PriceObservationRecord:
    product_id: int
    observed_at: datetime
    price_amount: float
    raw_price: str | None = None
    currency: str = "PEN"
    raw_unit: str | None = None
    normalized_unit_id: int | None = None
    source_url: str | None = None
    availability: str | None = None


class CostRepository:
    """Acceso de alto nivel a SQLite; todos los valores se parametrizan."""

    def __init__(self, database_path: Path, schema_path: Path | None = None) -> None:
        self.database_path = database_path
        self.schema_path = schema_path

    def initialize(self) -> None:
        if self.schema_path is None:
            raise ValueError("schema_path es obligatorio para inicializar el repositorio")
        initialize_database(self.database_path, self.schema_path)

    def upsert_provider(self, record: ProviderRecord) -> int:
        with DatabaseConnection(self.database_path) as database:
            database.execute(
                """
                INSERT INTO providers (name, website, is_active)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    website = excluded.website,
                    is_active = excluded.is_active
                """,
                (record.name, record.website, int(record.is_active)),
            )
            row = database.fetch_one("SELECT id FROM providers WHERE name = ?", (record.name,))
            if row is None:
                raise sqlite3.DatabaseError("No se pudo recuperar el proveedor creado")
            return int(row["id"])

    def upsert_category(self, name: str) -> int | None:
        normalized = name.strip()
        if not normalized:
            return None
        with DatabaseConnection(self.database_path) as database:
            database.execute(
                "INSERT INTO categories (name) VALUES (?) ON CONFLICT(name) DO NOTHING",
                (normalized,),
            )
            row = database.fetch_one("SELECT id FROM categories WHERE name = ?", (normalized,))
            return int(row["id"]) if row else None

    def upsert_unit(self, code: str | None, description: str | None = None) -> int | None:
        normalized = self._normalize_unit(code)
        if normalized is None:
            return None
        with DatabaseConnection(self.database_path) as database:
            database.execute(
                """
                INSERT INTO units (code, description) VALUES (?, ?)
                ON CONFLICT(code) DO UPDATE SET description = COALESCE(excluded.description, units.description)
                """,
                (normalized, description),
            )
            row = database.fetch_one("SELECT id FROM units WHERE code = ?", (normalized,))
            return int(row["id"]) if row else None

    def upsert_product(self, record: ProductRecord) -> int:
        with DatabaseConnection(self.database_path) as database:
            database.execute(
                """
                INSERT INTO products (
                    provider_id, category_id, unit_id, sku, name, normalized_name, product_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider_id, sku) DO UPDATE SET
                    category_id = excluded.category_id,
                    unit_id = excluded.unit_id,
                    name = excluded.name,
                    normalized_name = excluded.normalized_name,
                    product_url = excluded.product_url,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    record.provider_id,
                    record.category_id,
                    record.unit_id,
                    record.sku,
                    record.name,
                    record.normalized_name,
                    record.product_url,
                ),
            )
            if record.sku is None:
                row = database.fetch_one(
                    """
                    SELECT id FROM products
                    WHERE provider_id = ? AND name = ? AND normalized_name = ?
                    ORDER BY id DESC LIMIT 1
                    """,
                    (record.provider_id, record.name, record.normalized_name),
                )
            else:
                row = database.fetch_one(
                    "SELECT id FROM products WHERE provider_id = ? AND sku = ?",
                    (record.provider_id, record.sku),
                )
            if row is None:
                raise sqlite3.DatabaseError("No se pudo recuperar el producto creado")
            return int(row["id"])

    def insert_price_observation(self, record: PriceObservationRecord) -> int:
        with DatabaseConnection(self.database_path) as database:
            cursor = database.execute(
                """
                INSERT INTO price_observations (
                    product_id, observed_at, source_url, raw_price, price_amount,
                    currency, raw_unit, normalized_unit_id, availability
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.product_id,
                    record.observed_at.astimezone(timezone.utc).isoformat(),
                    record.source_url,
                    record.raw_price,
                    record.price_amount,
                    record.currency,
                    record.raw_unit,
                    record.normalized_unit_id,
                    record.availability,
                ),
            )
            return int(cursor.lastrowid)

    def list_latest_prices(self, limit: int = 500) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 10_000))
        with DatabaseConnection(self.database_path) as database:
            rows = database.fetch_all(
                """
                WITH ranked AS (
                    SELECT
                        po.*, ROW_NUMBER() OVER (
                            PARTITION BY po.product_id ORDER BY po.observed_at DESC, po.id DESC
                        ) AS row_number
                    FROM price_observations AS po
                )
                SELECT
                    p.name, p.normalized_name, p.sku, p.product_url,
                    pr.name AS provider_name, c.name AS category_name,
                    r.price_amount, r.currency, r.raw_unit, r.observed_at,
                    r.availability
                FROM ranked AS r
                JOIN products AS p ON p.id = r.product_id
                JOIN providers AS pr ON pr.id = p.provider_id
                LEFT JOIN categories AS c ON c.id = p.category_id
                WHERE r.row_number = 1
                ORDER BY r.observed_at DESC
                LIMIT ?
                """,
                (safe_limit,),
            )
            return [dict(row) for row in rows]

    @staticmethod
    def _normalize_unit(value: str | None) -> str | None:
        if not value:
            return None
        aliases = {
            "un": "UND",
            "und": "UND",
            "unidad": "UND",
            "kg": "KG",
            "kilogramo": "KG",
            "m": "M",
            "m2": "M2",
            "m²": "M2",
            "m3": "M3",
            "m³": "M3",
            "l": "L",
            "lt": "L",
        }
        normalized = value.strip().lower()
        return aliases.get(normalized, normalized.upper())

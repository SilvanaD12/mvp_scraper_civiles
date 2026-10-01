"""Contrato comun y politica de reintentos para scrapers."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

logger = logging.getLogger(__name__)


class ScraperError(RuntimeError):
    """Error controlado de extraccion."""


@dataclass(frozen=True, slots=True)
class ScrapeRequest:
    url: str
    search_term: str | None = None
    max_pages: int = 1
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RawProduct:
    provider_name: str
    name: str
    sku: str | None = None
    price: str | float | None = None
    currency: str = "PEN"
    unit: str | None = None
    url: str | None = None
    category: str | None = None
    availability: str | None = None
    raw_data: Mapping[str, Any] = field(default_factory=dict)
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseScraper(ABC):
    """Clase base con validacion de entrada, logging y reintentos."""

    provider_name: str

    def __init__(self, timeout_ms: int = 30_000, max_retries: int = 3, retry_delay_seconds: float = 1.0) -> None:
        self.timeout_ms = timeout_ms
        self.max_retries = max(0, max_retries)
        self.retry_delay_seconds = max(0.0, retry_delay_seconds)

    def scrape(self, request: ScrapeRequest) -> Sequence[RawProduct]:
        if not request.url.strip():
            raise ScraperError("La URL de extraccion es obligatoria")
        if request.max_pages < 1:
            raise ScraperError("max_pages debe ser mayor o igual a 1")

        attempts = self.max_retries + 1
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                products = list(self._scrape_once(request))
                logger.info(
                    "Extraccion finalizada",
                    extra={"structured": {"provider": self.provider_name, "count": len(products), "attempt": attempt}},
                )
                return products
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Fallo de extraccion; se evaluara reintento",
                    extra={"structured": {"provider": self.provider_name, "attempt": attempt, "attempts": attempts}},
                    exc_info=True,
                )
                if attempt < attempts:
                    time.sleep(self.retry_delay_seconds * attempt)

        raise ScraperError(f"No se pudo extraer informacion de {self.provider_name}") from last_error

    @abstractmethod
    def _scrape_once(self, request: ScrapeRequest) -> Sequence[RawProduct]:
        """Ejecuta un intento concreto de extraccion."""

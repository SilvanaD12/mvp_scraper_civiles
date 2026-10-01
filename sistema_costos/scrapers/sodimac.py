"""Extractor inicial de Sodimac basado en Playwright y BeautifulSoup."""

from __future__ import annotations

import json
import logging
from typing import Any, Sequence
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, RawProduct, ScrapeRequest, ScraperError

logger = logging.getLogger(__name__)


class SodimacScraper(BaseScraper):
    """Implementacion MVP con selectores tolerantes a cambios del proveedor."""

    provider_name = "Sodimac"

    def __init__(
        self,
        timeout_ms: int = 30_000,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
        headless: bool = True,
    ) -> None:
        super().__init__(timeout_ms, max_retries, retry_delay_seconds)
        self.headless = headless

    def _scrape_once(self, request: ScrapeRequest) -> Sequence[RawProduct]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ScraperError("Playwright no esta instalado. Ejecute pip install -r requirements.txt") from exc

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.headless)
                try:
                    page = browser.new_page(
                        viewport={"width": 1440, "height": 900},
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 Chrome/120 Safari/537.36"
                        ),
                    )
                    page.goto(request.url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                    page.wait_for_timeout(750)
                    html = page.content()
                finally:
                    browser.close()
        except Exception as exc:
            raise ScraperError(f"Playwright no pudo cargar {request.url}") from exc

        return self.parse_html(html, request.url)

    def parse_html(self, html: str, base_url: str) -> Sequence[RawProduct]:
        """Permite probar el parser sin navegador y facilita su evolucion."""

        soup = BeautifulSoup(html, "html.parser")
        products: list[RawProduct] = []
        seen: set[tuple[str, str]] = set()

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                payload = json.loads(script.get_text(strip=True))
            except json.JSONDecodeError:
                continue
            for item in self._iter_jsonld_products(payload):
                product = self._product_from_jsonld(item, base_url)
                if product and self._append_unique(products, seen, product):
                    continue

        card_selectors = (
            "[data-testid*='product']",
            "[class*='product-card']",
            "[class*='product-item']",
            "article",
        )
        for card in soup.select(", ".join(card_selectors)):
            name = self._text(card.select_one("[data-testid*='name'], .product-name, h2, h3"))
            price = self._text(card.select_one("[data-testid*='price'], .price, [class*='price']"))
            if not name or not price:
                continue
            link = card.select_one("a[href]")
            product = RawProduct(
                provider_name=self.provider_name,
                name=name,
                price=price,
                url=urljoin(base_url, link.get("href", "")) if link else base_url,
                raw_data={"source": "html-card"},
            )
            self._append_unique(products, seen, product)

        return products

    @staticmethod
    def _iter_jsonld_products(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict):
            if payload.get("@type") == "Product":
                return [payload]
            items = payload.get("itemListElement", [])
            return [item for item in items if isinstance(item, dict) and item.get("@type") == "Product"]
        if isinstance(payload, list):
            products: list[dict[str, Any]] = []
            for item in payload:
                products.extend(SodimacScraper._iter_jsonld_products(item))
            return products
        return []

    def _product_from_jsonld(self, item: dict[str, Any], base_url: str) -> RawProduct | None:
        name = self._text_value(item.get("name"))
        if not name:
            return None
        offers = item.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not isinstance(offers, dict):
            offers = {}
        return RawProduct(
            provider_name=self.provider_name,
            name=name,
            sku=self._text_value(item.get("sku")),
            price=offers.get("price"),
            currency=self._text_value(offers.get("priceCurrency")) or "PEN",
            url=urljoin(base_url, self._text_value(item.get("url")) or base_url),
            availability=self._text_value(offers.get("availability")),
            raw_data={"source": "json-ld", "brand": item.get("brand")},
        )

    @staticmethod
    def _append_unique(products: list[RawProduct], seen: set[tuple[str, str]], product: RawProduct) -> bool:
        key = (product.sku or product.url or product.name, str(product.price))
        if key in seen:
            return False
        seen.add(key)
        products.append(product)
        return True

    @staticmethod
    def _text(node: Any) -> str | None:
        return node.get_text(" ", strip=True) if node is not None else None

    @staticmethod
    def _text_value(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, dict):
            value = value.get("name") or value.get("@id")
        text = str(value).strip()
        return text or None

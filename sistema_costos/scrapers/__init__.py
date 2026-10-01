"""Bots de extraccion desacoplados por proveedor."""

from .base_scraper import BaseScraper, RawProduct, ScrapeRequest, ScraperError

__all__ = ["BaseScraper", "RawProduct", "ScrapeRequest", "ScraperError", "SodimacScraper"]


def __getattr__(name: str) -> object:
    """Carga adapters concretos solo cuando se solicitan."""

    if name == "SodimacScraper":
        from .sodimac import SodimacScraper

        return SodimacScraper
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

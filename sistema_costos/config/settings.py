"""Configuracion centralizada, rutas y logging estructurado."""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

APP_NAME: Final[str] = "Ceniteg Solutions - Sistema de Costos"
PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
RESOURCE_ROOT: Final[Path] = Path(getattr(sys, "_MEIPASS", PACKAGE_ROOT))


@dataclass(frozen=True, slots=True)
class Settings:
    """Valores de runtime inmutables para cada ejecucion de la aplicacion."""

    app_name: str
    data_dir: Path
    database_path: Path
    schema_path: Path
    exports_dir: Path
    logs_dir: Path
    log_level: int = logging.INFO
    scraper_timeout_ms: int = 30_000
    scraper_max_retries: int = 3
    scraper_retry_delay_seconds: float = 1.0
    browser_headless: bool = True

    def ensure_directories(self) -> None:
        """Crea solo los directorios de datos que la aplicacion necesita."""

        for directory in (self.data_dir, self.exports_dir, self.logs_dir):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Construye la configuracion usando variables de entorno opcionales."""

    configured_data_dir = os.getenv("CENITEG_DATA_DIR")
    data_dir = Path(configured_data_dir) if configured_data_dir else Path.home() / "CenitegSolutions" / "costos_data"
    return Settings(
        app_name=APP_NAME,
        data_dir=data_dir,
        database_path=data_dir / "costos.db",
        schema_path=RESOURCE_ROOT / "database" / "schema.sql",
        exports_dir=data_dir / "exports",
        logs_dir=data_dir / "logs",
    )


class JsonFormatter(logging.Formatter):
    """Formatea registros para facilitar su lectura y posterior analisis."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        structured = getattr(record, "structured", None)
        if isinstance(structured, dict):
            payload["context"] = structured
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, default=str)


def configure_logging(settings: Settings | None = None) -> None:
    """Configura consola y archivo rotativo sin duplicar handlers."""

    active_settings = settings or get_settings()
    active_settings.ensure_directories()
    root_logger = logging.getLogger()
    if getattr(root_logger, "_ceniteg_configured", False):
        return

    root_logger.setLevel(active_settings.log_level)
    formatter = JsonFormatter()
    file_handler = logging.handlers.RotatingFileHandler(
        active_settings.logs_dir / "application.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    setattr(root_logger, "_ceniteg_configured", True)

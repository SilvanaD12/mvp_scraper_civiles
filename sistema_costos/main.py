"""Punto de entrada para ejecucion local y empaquetado futuro."""

from __future__ import annotations

import logging

from .config.settings import configure_logging, get_settings
from .database.connection import initialize_database
from .ui.app import CostApp


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    logger = logging.getLogger(__name__)
    initialize_database(settings.database_path, settings.schema_path)
    logger.info("Aplicacion iniciada", extra={"structured": {"database": str(settings.database_path)}})
    application = CostApp(settings)
    application.mainloop()


if __name__ == "__main__":
    main()

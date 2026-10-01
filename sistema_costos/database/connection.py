"""Conexion SQLite con transacciones explicitas y Foreign Keys activadas."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence


class DatabaseError(RuntimeError):
    """Error de infraestructura de base de datos."""


class DatabaseConnection:
    """Context manager que garantiza commit, rollback y cierre de SQLite."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._connection: sqlite3.Connection | None = None

    def __enter__(self) -> "DatabaseConnection":
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._connection = sqlite3.connect(str(self.database_path), timeout=30)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA journal_mode = WAL")
        except sqlite3.Error as exc:
            raise DatabaseError(f"No se pudo abrir SQLite: {self.database_path}") from exc
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if self._connection is None:
            return
        try:
            if exc_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()
        finally:
            self._connection.close()
            self._connection = None

    @property
    def raw(self) -> sqlite3.Connection:
        if self._connection is None:
            raise DatabaseError("La conexion SQLite no esta activa")
        return self._connection

    def execute(self, query: str, parameters: Sequence[Any] = ()) -> sqlite3.Cursor:
        try:
            return self.raw.execute(query, parameters)
        except sqlite3.Error as exc:
            raise DatabaseError("Fallo al ejecutar una consulta SQLite") from exc

    def executemany(self, query: str, parameters: Sequence[Sequence[Any]]) -> sqlite3.Cursor:
        try:
            return self.raw.executemany(query, parameters)
        except sqlite3.Error as exc:
            raise DatabaseError("Fallo al ejecutar una operacion SQLite por lote") from exc

    def executescript(self, script: str) -> None:
        try:
            self.raw.executescript(script)
        except sqlite3.Error as exc:
            raise DatabaseError("Fallo al inicializar el esquema SQLite") from exc

    def fetch_one(self, query: str, parameters: Sequence[Any] = ()) -> sqlite3.Row | None:
        return self.execute(query, parameters).fetchone()

    def fetch_all(self, query: str, parameters: Sequence[Any] = ()) -> list[sqlite3.Row]:
        return self.execute(query, parameters).fetchall()


@contextmanager
def connection(database_path: Path) -> Iterator[DatabaseConnection]:
    """Expone el contexto de conexion como funcion utilitaria."""

    with DatabaseConnection(database_path) as database:
        yield database


def initialize_database(database_path: Path, schema_path: Path) -> None:
    """Crea las tablas e indices idempotentemente."""

    if not schema_path.exists():
        raise DatabaseError(f"No se encontro el esquema: {schema_path}")
    with DatabaseConnection(database_path) as database:
        database.executescript(schema_path.read_text(encoding="utf-8"))

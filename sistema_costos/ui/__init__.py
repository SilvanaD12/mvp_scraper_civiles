"""Interfaz grafica de escritorio."""

__all__ = ["CostApp", "ReferencesApp"]


def __getattr__(name):
    if name == 'CostApp':
        from .app import CostApp
        return CostApp
    if name == 'ReferencesApp':
        from .references_app import ReferencesApp
        return ReferencesApp
    raise AttributeError(name)

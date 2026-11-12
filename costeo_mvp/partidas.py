"""Cálculo por metrado a partir de un precio unitario guardado."""

from decimal import Decimal, ROUND_HALF_UP, localcontext

from sistema_costos.services.extraccion_costos import decimal_seguro


def precio_partida(fila: dict) -> Decimal:
    if fila.get("estado") == "rechazado":
        raise ValueError("La partida está rechazada.")
    # Las partidas guardadas antes del campo tipo_monto pueden tenerlo vacío.
    if fila.get("tipo_monto") not in (None, "", "precio_unitario"):
        raise ValueError("Selecciona una partida con precio unitario.")
    if not (fila.get("unidad") or "").strip():
        raise ValueError("La partida no tiene unidad registrada.")
    if fila.get("moneda") not in ("PEN", "USD"):
        raise ValueError("La partida necesita una moneda registrada en PEN o USD.")
    precio = decimal_seguro((fila.get("precio_unitario_texto") or "").strip())
    if precio is None or precio <= 0:
        raise ValueError("La partida necesita un precio unitario válido y mayor que cero.")
    return precio


def calcular_partida(fila: dict, metrado: str) -> dict:
    precio = precio_partida(fila)
    cantidad = decimal_seguro(metrado.strip(), cantidad=True)
    if cantidad is None or cantidad <= 0:
        raise ValueError("Ingresa un metrado mayor que cero con hasta cuatro decimales.")

    with localcontext() as contexto:
        contexto.prec = 64
        parcial = (cantidad * precio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {**fila, "metrado": cantidad, "precio": precio, "parcial": parcial}


def subtotales_por_moneda(partidas) -> dict:
    subtotales = {}
    with localcontext() as contexto:
        contexto.prec = 64
        for partida in partidas:
            moneda = partida["moneda"]
            subtotales[moneda] = subtotales.get(moneda, Decimal("0.00")) + partida["parcial"]
    return subtotales

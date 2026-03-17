from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

_MONEY_QUANT = Decimal("0.01")
_HUNDRED = Decimal("100")


def to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value: Any) -> float:
    return float(to_decimal(value).quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP))


def percentage(numerator: Any, denominator: Any) -> float:
    den = to_decimal(denominator)
    if den == 0:
        return 0.0
    num = to_decimal(numerator)
    return money((num / den) * _HUNDRED)

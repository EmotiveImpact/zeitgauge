"""Sahm rule (Claudia Sahm, 2019).

The indicator is the three-month average of the unemployment rate minus the
lowest three-month average in the previous twelve months. A reading of 0.5
percentage points or more has marked the start of every US recession since 1970.

It works for the UK too, though it has been tested far less there, so treat a UK
reading as supporting evidence rather than a trigger.
"""

from __future__ import annotations

TRIGGER = 0.5


def _moving_average(values: list[float], window: int = 3) -> list[float]:
    return [sum(values[i - window + 1:i + 1]) / window for i in range(window - 1, len(values))]


def sahm_series(unemployment: list[float]) -> list[float]:
    """Return the Sahm indicator for every month where it can be computed.

    unemployment: monthly rates, oldest first. Needs at least 15 months
    (3 for the first average plus 12 months of history before it).
    """
    ma = _moving_average(unemployment, 3)
    out = []
    for i in range(12, len(ma)):
        prior_min = min(ma[i - 12:i])
        out.append(round(ma[i] - prior_min, 3))
    return out


def sahm_latest(unemployment: list[float]) -> tuple[float, float | None]:
    """Latest and previous Sahm readings, ready for a readings file."""
    s = sahm_series(unemployment)
    if not s:
        raise ValueError("need at least 15 monthly unemployment readings")
    return s[-1], (s[-2] if len(s) > 1 else None)


def triggered(value: float) -> bool:
    return value >= TRIGGER

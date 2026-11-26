"""Optional: Google Trends as a fast 'culture' signal, via trendspyg (MIT).

Search interest moves weeks before official data. Useful for:
  - spotting product waves early (for example 'press on nails', 'air fryer')
  - checking a playbook theme against what people actually search for
  - measuring US to UK lag for the culture channel in spillover.py

Install with:  pip install "trendspyg[analysis]"
This module imports trendspyg only when called, so the core stays light.
Trends values are relative (0 to 100 within the chosen window), so compare
shapes and timing, never raw levels across separate downloads.
"""

from __future__ import annotations


def interest_over_time(keywords: list[str], geo: str = "GB", timeframe: str = "today 5-y"):
    try:
        from trendspyg.compat.request import TrendReq
    except ImportError as e:  # pragma: no cover
        raise RuntimeError('Google Trends needs: pip install "trendspyg[analysis]"') from e
    req = TrendReq(hl="en-GB", tz=0)
    req.build_payload(keywords, timeframe=timeframe, geo=geo)
    return req.interest_over_time()


def lead_lag_months(us_series: list[float], uk_series: list[float], max_lag: int = 12) -> int:
    """Lag (in periods) at which the US series best matches the UK series.

    A simple cross-correlation. Positive means the US leads the UK.
    """
    def corr(a: list[float], b: list[float]) -> float:
        n = len(a)
        if n < 3:
            return 0.0
        ma, mb = sum(a) / n, sum(b) / n
        va = sum((x - ma) ** 2 for x in a) ** 0.5
        vb = sum((y - mb) ** 2 for y in b) ** 0.5
        if not va or not vb:
            return 0.0
        return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (va * vb)

    best_lag, best = 0, -2.0
    for lag in range(0, max_lag + 1):
        a = us_series[: len(us_series) - lag] if lag else us_series
        b = uk_series[lag:]
        n = min(len(a), len(b))
        c = corr(a[-n:], b[-n:]) if n else 0.0
        if c > best:
            best, best_lag = c, lag
    return best_lag

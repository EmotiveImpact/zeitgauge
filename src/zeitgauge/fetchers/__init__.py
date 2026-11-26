"""Fetch raw series from public statistics sites.

Each fetcher has two halves:
  - parse_*(text) turns a downloaded file into [(date, value), ...] oldest first.
    These are pure functions and are covered by tests with saved fixtures.
  - fetch_*(...) downloads the file and calls the parser.

The network halves need ordinary internet access. They have not been run from
the build container (its proxy blocks these sites), so run `zeitgauge fetch`
on your own machine or in GitHub Actions the first time and check the output.
"""

from __future__ import annotations

import urllib.request

USER_AGENT = "zeitgauge/0.1 (open-source economic dashboard)"
Series = list[tuple[str, float]]


def get_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed https hosts)
        return resp.read().decode("utf-8", errors="replace")


def latest_two(series: Series) -> tuple[float | None, float | None, str | None]:
    """Latest value, the one before it, and the latest period label."""
    if not series:
        return None, None, None
    latest_date, latest = series[-1]
    previous = series[-2][1] if len(series) > 1 else None
    return latest, previous, latest_date


def year_on_year(series: Series, periods: int = 12) -> Series:
    """Percentage change on the same period a year earlier (for index levels such as CPI)."""
    out = []
    for i in range(periods, len(series)):
        base = series[i - periods][1]
        if base:
            out.append((series[i][0], round((series[i][1] / base - 1) * 100, 2)))
    return out

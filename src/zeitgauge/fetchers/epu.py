"""Economic Policy Uncertainty, daily (Baker, Bloom and Davis).

Built from newspaper articles that mention the economy, policy and uncertainty
together. Free under CC BY 4.0: credit "Baker, Bloom and Davis,
policyuncertainty.com" wherever the number is shown.

UK daily: https://www.policyuncertainty.com/media/UK_Daily_Policy_Data.csv
  columns: day,month,year,daily_policy_index
US daily: FRED series USEPUINDXD (use the fred fetcher instead).

Single days are noisy (some days read 0 when few papers are scanned), so the
pulse looks at a seven-day average rather than any one day.
"""

from __future__ import annotations

import csv
import io

from . import Series, get_text

UK_DAILY = "https://www.policyuncertainty.com/media/UK_Daily_Policy_Data.csv"


def parse_epu_daily(text: str) -> Series:
    reader = csv.DictReader(io.StringIO(text))
    out = []
    for row in reader:
        try:
            d, m, y = int(row["day"]), int(row["month"]), int(row["year"])
            value = float(row["daily_policy_index"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append((f"{y:04d}-{m:02d}-{d:02d}", value))
    return sorted(out)


def fetch_epu_daily(url: str = UK_DAILY) -> Series:
    return parse_epu_daily(get_text(url, timeout=60))

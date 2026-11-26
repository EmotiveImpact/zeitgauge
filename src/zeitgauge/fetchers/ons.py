"""Office for National Statistics time series.

Every ONS time series page has a JSON twin: add /data to the page path.
Example: https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7g7/mm23/data

The JSON holds 'years', 'quarters' and 'months' lists. Each entry has 'date'
(for example "2026 OCT") and 'value' (a string). We prefer months, then
quarters, then years, because Zeitgauge updates monthly.

A licensed alternative is the onspy package (GPL-3.0). We do not copy its code;
this file is a small independent client so Zeitgauge can stay MIT-licensed.
"""

from __future__ import annotations

import json

from . import Series, get_text

BASE = "https://www.ons.gov.uk"


def parse_ons(text: str, frequency: str | None = None) -> Series:
    doc = json.loads(text)
    order = [frequency] if frequency else ["months", "quarters", "years"]
    for key in order:
        rows = doc.get(key) or []
        out = []
        for r in rows:
            v = str(r.get("value", "")).strip()
            if v in ("", ".", "x", ".."):
                continue
            try:
                out.append((r["date"], float(v)))
            except ValueError:
                continue
        if out:
            return out
    return []


def fetch_ons(path: str, frequency: str | None = None) -> Series:
    return parse_ons(get_text(f"{BASE}{path}/data"), frequency)

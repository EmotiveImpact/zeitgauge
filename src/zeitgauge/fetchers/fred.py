"""FRED (Federal Reserve Bank of St Louis) series, no API key needed.

The public graph CSV endpoint returns two columns: a date column (named
'observation_date' or 'DATE' depending on the day) and the series ID.
Missing values are a single dot.
Example: https://fred.stlouisfed.org/graph/fredgraph.csv?id=UMCSENT

For heavy use, register a free API key and switch to the official API.
"""

from __future__ import annotations

import csv
import io

from . import Series, get_text

BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="


def parse_fred(text: str) -> Series:
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header or len(header) < 2:
        return []
    out = []
    for row in reader:
        if len(row) < 2 or row[1].strip() in ("", "."):
            continue
        try:
            out.append((row[0], float(row[1])))
        except ValueError:
            continue
    return out


def fetch_fred(series_id: str) -> Series:
    return parse_fred(get_text(BASE + series_id))

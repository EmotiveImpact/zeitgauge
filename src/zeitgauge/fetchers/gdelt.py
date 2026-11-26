"""GDELT DOC 2.0 API: what the world's news is saying, updated every 15 minutes.

Free, no key. Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

Two modes are used:
  - timelinetone: average tone of matching articles (below 0 is negative coverage)
  - timelinevol:  matching articles as a share of all coverage GDELT monitors,
                  which cancels out the daily and weekend rhythm of publishing

Time step depends on the window: under 72 hours gives 15-minute points, 72 hours
to a week gives hourly points, and anything longer gives daily points.
Country filters use FIPS codes: the UK is `sourcecountry:UK`, the US is `US`.

GDELT asks for no more than one request every five seconds, so fetch_gdelt
waits between calls.

JSON shape:
  {"query_details": {"title": "...", "date_resolution": "day"},
   "timeline": [{"series": "Average Tone",
                 "data": [{"date": "20251025T000000Z", "value": 0.56}, ...]}]}
"""

from __future__ import annotations

import json
import time
import urllib.parse

from . import Series, get_text

BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
MIN_GAP_SECONDS = 5.5
_last_call = 0.0


def _iso(stamp: str) -> str:
    """'20251025T000000Z' -> '2025-10-25', '20251025T130000Z' -> '2025-10-25T13:00'."""
    s = stamp.strip()
    day = f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    if len(s) >= 13 and s[8] == "T" and s[9:13] != "0000":
        return f"{day}T{s[9:11]}:{s[11:13]}"
    return day


def parse_gdelt_timeline(text: str, series: str | None = None) -> Series:
    """First timeline series (or the one named) as [(date, value), ...] oldest first."""
    if not text.strip():
        return []
    doc = json.loads(text)
    timelines = doc.get("timeline") or []
    if not timelines:
        return []
    chosen = timelines[0]
    if series:
        for t in timelines:
            if t.get("series") == series:
                chosen = t
                break
    out = []
    for point in chosen.get("data", []):
        try:
            out.append((_iso(point["date"]), float(point["value"])))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(out)


def gdelt_url(query: str, mode: str = "timelinetone", timespan: str = "120d") -> str:
    params = {"query": query, "mode": mode, "format": "json", "timespan": timespan}
    return BASE + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def fetch_gdelt(query: str, mode: str = "timelinetone", timespan: str = "120d") -> Series:
    global _last_call
    wait = MIN_GAP_SECONDS - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    try:
        return parse_gdelt_timeline(get_text(gdelt_url(query, mode, timespan), timeout=60))
    finally:
        _last_call = time.monotonic()

"""X (formerly Twitter) API v2: pay per use.

Zeitgauge only calls the recent counts endpoint, which returns how many posts
matched a query per day or per hour over the last 7 days, without reading any
posts. One call a day fills the daily signal; the first call fills in the whole
week. Hourly counts feed the optional spike alert.

Docs: https://docs.x.com/x-api/posts/counts/introduction
Reply: {"data": [{"start": "...", "end": "...", "tweet_count": 5}], "meta": {...}}
(newer docs call the field post_count, so both are accepted).
"""

from __future__ import annotations

import urllib.parse
from datetime import date

BASE = "https://api.x.com/2/tweets/counts/recent"


def requests_per_day(settings: dict, region_settings: dict) -> int:
    return 1


def counts(query: str, granularity: str, env: dict, http) -> list[tuple[str, str, float]]:
    """[(start, end, count), ...] oldest first."""
    url = BASE + "?" + urllib.parse.urlencode({"query": query, "granularity": granularity})
    reply = http.get_json(url, headers={"Authorization": f"Bearer {env['X_BEARER_TOKEN']}"})
    out = []
    for b in reply.get("data", []):
        n = b.get("tweet_count", b.get("post_count"))
        if n is None:
            continue
        out.append((b["start"], b["end"], float(n)))
    return sorted(out)


def count_rows(settings: dict, region_settings: dict, day: date, env: dict, http) -> list[tuple]:
    """Every complete day in the last week, up to and including `day`."""
    rows = []
    for start, _end, n in counts(region_settings["query"], "day", env, http):
        d = start[:10]
        if d <= day.isoformat():
            rows.append((d, "all", int(n), False))
    return rows


def hourly_series(query: str, env: dict, http) -> list[tuple[str, float]]:
    """Hourly counts for the past week, dropping the hour still in progress."""
    buckets = counts(query, "hour", env, http)
    return [(start[:16], n) for start, _end, n in buckets[:-1]]

"""Wikipedia pageviews: what people are reading up on, daily.

Free, no key, from the Wikimedia REST API. Docs:
https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html

Agent "user" leaves out known bots. English Wikipedia is read worldwide, so treat
it as an attention signal for the English-speaking world rather than the UK alone.
The API gives daily (not hourly) figures, usually complete by the next morning UTC.

JSON shape:
  {"items": [{"article": "Recession", "timestamp": "2026100100", "views": 1234, ...}]}
"""

from __future__ import annotations

import json
import urllib.parse
from collections import defaultdict
from datetime import date, timedelta

from . import Series, get_text

BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"


def parse_pageviews(text: str) -> Series:
    """Daily views as [(date, views), ...], summed if the file holds several articles."""
    totals: dict[str, float] = defaultdict(float)
    for item in json.loads(text).get("items", []):
        ts = str(item.get("timestamp", ""))
        if len(ts) < 8:
            continue
        totals[f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"] += float(item.get("views", 0))
    return sorted(totals.items())


def pageviews_url(article: str, start: date, end: date, project: str = "en.wikipedia") -> str:
    title = urllib.parse.quote(article.replace(" ", "_"), safe="")
    return f"{BASE}/{project}/all-access/user/{title}/daily/{start:%Y%m%d}00/{end:%Y%m%d}00"


def fetch_pageviews(articles: list[str], days: int = 150, project: str = "en.wikipedia",
                    today: date | None = None) -> Series:
    """Total daily views across the articles, ending yesterday (today is never complete)."""
    end = (today or date.today()) - timedelta(days=1)
    start = end - timedelta(days=days)
    totals: dict[str, float] = defaultdict(float)
    for article in articles:
        for d, v in parse_pageviews(get_text(pageviews_url(article, start, end, project))):
            totals[d] += v
    return sorted(totals.items())

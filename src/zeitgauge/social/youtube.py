"""YouTube Data API v3: free within a daily quota.

10,000 units a day; each search.list page costs 100 units. Counts new videos
published on one day that match each term, up to 50 per page.

regionCode limits results to videos watchable in that country (not made
there), so treat this as a rough English-language signal.
"""

from __future__ import annotations

import urllib.parse
from datetime import date, timedelta

BASE = "https://www.googleapis.com/youtube/v3/search"
UNITS_PER_PAGE = 100


def requests_per_day(settings: dict, region_settings: dict) -> int:
    return 0  # free within quota


def quota_units(settings: dict, region_settings: dict) -> int:
    return UNITS_PER_PAGE * int(settings.get("max_pages", 1)) * len(region_settings.get("terms", []))


def count_rows(settings: dict, region_settings: dict, day: date, env: dict, http) -> list[tuple]:
    key = env["YOUTUBE_API_KEY"]
    max_pages = int(settings.get("max_pages", 1))
    after, before = f"{day.isoformat()}T00:00:00Z", f"{(day + timedelta(days=1)).isoformat()}T00:00:00Z"
    rows = []
    for term in region_settings.get("terms", []):
        count, token, capped = 0, None, False
        for page in range(max_pages):
            params = {"part": "id", "q": term, "type": "video", "maxResults": 50,
                      "publishedAfter": after, "publishedBefore": before,
                      "regionCode": region_settings.get("region_code", "GB"), "relevanceLanguage": "en", "key": key}
            if token:
                params["pageToken"] = token
            reply = http.get_json(BASE + "?" + urllib.parse.urlencode(params))
            count += len(reply.get("items", []))
            token = reply.get("nextPageToken")
            if not token:
                break
            if page == max_pages - 1:
                capped = True
        rows.append((day.isoformat(), term, count, capped))
    return rows

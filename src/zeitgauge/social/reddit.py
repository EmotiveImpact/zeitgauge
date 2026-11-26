"""Reddit: official OAuth API, only with Reddit's written approval.

The free tier is for non-commercial use. A paid product needs a commercial
agreement. Reddit stopped approving new public API requests on 31 October 2026,
so this adapter is here for anyone who already has, or later gets, approved
access. It will not run until approved_use = true in config/social.toml.

Counts posts created on one day that match each term in each subreddit.
"""

from __future__ import annotations

import base64
import urllib.parse
from datetime import date, datetime, timedelta, timezone

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"


def requests_per_day(settings: dict, region_settings: dict) -> int:
    return 0  # not metered per request here; governed by the agreement


def _token(env: dict, http) -> str:
    basic = base64.b64encode(f"{env['REDDIT_CLIENT_ID']}:{env['REDDIT_CLIENT_SECRET']}".encode()).decode()
    reply = http.post_json(TOKEN_URL, form={"grant_type": "client_credentials"},
                           headers={"Authorization": f"Basic {basic}"})
    return reply["access_token"]


def count_rows(settings: dict, region_settings: dict, day: date, env: dict, http) -> list[tuple]:
    auth = {"Authorization": f"Bearer {_token(env, http)}"}
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp()
    end = start + timedelta(days=1).total_seconds()
    rows = []
    for term in region_settings.get("terms", []):
        count, capped = 0, False
        for sub in region_settings.get("subreddits", []):
            params = {"q": term, "restrict_sr": 1, "sort": "new", "t": "week", "limit": 100}
            reply = http.get_json(f"{API}/r/{sub}/search?" + urllib.parse.urlencode(params), headers=auth)
            children = reply.get("data", {}).get("children", [])
            count += sum(1 for c in children if start <= float(c.get("data", {}).get("created_utc", 0)) < end)
            capped = capped or len(children) >= 100
        rows.append((day.isoformat(), term, count, capped))
    return rows

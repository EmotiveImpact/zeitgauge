"""Bluesky: free, through the official AT Protocol API.

Search needs a signed-in session: the public AppView host refuses search
requests. Sign in with an app password (never the main password), then call
app.bsky.feed.searchPosts on your PDS, which forwards it to the AppView.

Counts posts for each term on one day, using the structured since/until
parameters (since is inclusive, until is not). Pages of 100 up to max_pages; a
term that fills every page is marked as capped, meaning the true count is higher.
"""

from __future__ import annotations

import urllib.parse
from datetime import date, timedelta


def requests_per_day(settings: dict, region_settings: dict) -> int:
    return 0  # free


def _session(settings: dict, env: dict, http) -> str:
    pds = settings.get("pds", "https://bsky.social").rstrip("/")
    reply = http.post_json(f"{pds}/xrpc/com.atproto.server.createSession",
                           {"identifier": env["BLUESKY_HANDLE"], "password": env["BLUESKY_APP_PASSWORD"]})
    return reply["accessJwt"]


def count_rows(settings: dict, region_settings: dict, day: date, env: dict, http) -> list[tuple]:
    pds = settings.get("pds", "https://bsky.social").rstrip("/")
    token = _session(settings, env, http)
    auth = {"Authorization": f"Bearer {token}"}
    max_pages = int(settings.get("max_pages", 5))
    since, until = f"{day.isoformat()}T00:00:00Z", f"{(day + timedelta(days=1)).isoformat()}T00:00:00Z"
    rows = []
    for term in region_settings.get("terms", []):
        count, cursor, capped = 0, None, False
        for page in range(max_pages):
            params = {"q": term, "since": since, "until": until, "limit": 100, "sort": "latest"}
            if settings.get("lang"):
                params["lang"] = settings["lang"]
            if cursor:
                params["cursor"] = cursor
            reply = http.get_json(f"{pds}/xrpc/app.bsky.feed.searchPosts?" + urllib.parse.urlencode(params),
                                  headers=auth)
            posts = reply.get("posts", [])
            count += len(posts)
            cursor = reply.get("cursor")
            if not cursor or len(posts) < 100:
                break
            if page == max_pages - 1:
                capped = True
        rows.append((day.isoformat(), term, count, capped))
    return rows

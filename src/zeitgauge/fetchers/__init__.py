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

import json
import os
import urllib.request

# Some services (Wikimedia in particular) ask automated clients for a way to get
# in touch. Set ZEITGAUGE_CONTACT (a URL or address) as a repository variable to
# add one; nothing personal is sent by default.
USER_AGENT = "zeitgauge/0.2 (open-source economic dashboard)"
Series = list[tuple[str, float]]


def user_agent() -> str:
    contact = os.environ.get("ZEITGAUGE_CONTACT", "").strip()
    return f"{USER_AGENT[:-1]}; {contact})" if contact else USER_AGENT


def get_text(url: str, timeout: int = 30, headers: dict | None = None) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent(), "Accept": "*/*", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed https hosts)
        return resp.read().decode("utf-8", errors="replace")


def get_json(url: str, timeout: int = 30, headers: dict | None = None) -> dict:
    return json.loads(get_text(url, timeout=timeout, headers={"Accept": "application/json", **(headers or {})}))


def post_json(url: str, payload: dict | None = None, timeout: int = 30, headers: dict | None = None,
              form: dict | None = None) -> dict:
    """POST JSON (or a form, when form= is given) and return the decoded JSON reply."""
    import urllib.parse
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        ctype = "application/x-www-form-urlencoded"
    else:
        body = json.dumps(payload or {}).encode()
        ctype = "application/json"
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"User-Agent": user_agent(), "Content-Type": ctype,
                                          "Accept": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        text = resp.read().decode("utf-8", errors="replace")
    return json.loads(text) if text.strip() else {}


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

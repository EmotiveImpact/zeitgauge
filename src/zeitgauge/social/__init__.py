"""Social media signals, switched on one platform at a time.

config/social.toml holds a switch per platform. A platform runs only when it is
enabled there, its keys are present (as environment variables, which GitHub
Actions fills from repository secrets) and the platform offers an official
route for this use. Nothing in this package scrapes websites.

Each platform's adapter returns rows of (date, term, count, capped). Counts are
stored per region in data/social/<region>/<platform>.csv, and the daily pulse
reads them as one extra signal per platform once enough days have built up.

Paid platforms (X) are guarded by a monthly budget kept in data/social/spend.json.
"""

from __future__ import annotations

import csv
import io
import json
import os
import tomllib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from ..config import ROOT
from ..fetchers import Series
from ..pulse import PulseSignal

SOCIAL_CONFIG = ROOT / "config" / "social.toml"
SOCIAL_DATA_DIR = ROOT / "data" / "social"
PLATFORMS = ("bluesky", "youtube", "x", "reddit", "tiktok")
FIELDS = ["date", "term", "count", "capped"]


def load_social(path: Path = SOCIAL_CONFIG) -> dict:
    return tomllib.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}


class Http:
    """Thin wrapper so tests can swap in canned replies."""

    def get_json(self, url: str, headers: dict | None = None) -> dict:
        from ..fetchers import get_json
        return get_json(url, headers=headers)

    def post_json(self, url: str, payload: dict | None = None, headers: dict | None = None,
                  form: dict | None = None) -> dict:
        from ..fetchers import post_json
        return post_json(url, payload, headers=headers, form=form)


@dataclass
class Status:
    platform: str
    label: str
    enabled: bool
    available: bool
    ready: bool
    missing: list[str] = field(default_factory=list)
    cost: str = ""
    note: str = ""
    blocker: str = ""


def status(cfg: dict, env: dict | None = None) -> list[Status]:
    env = os.environ if env is None else env
    out = []
    for p in PLATFORMS:
        s = cfg.get(p, {})
        enabled = bool(s.get("enabled", False))
        available = bool(s.get("available", True))
        missing = [k for k in s.get("secrets", []) if not str(env.get(k, "")).strip()]
        blocker = ""
        if not available:
            blocker = "No official route for this use"
        elif not enabled:
            blocker = "Switched off"
        elif missing:
            blocker = "Missing secrets: " + ", ".join(missing)
        elif p == "reddit" and not s.get("approved_use", False):
            blocker = "Waiting for Reddit's written approval (set approved_use = true once you have it)"
        out.append(Status(platform=p, label=s.get("label", p.title()), enabled=enabled, available=available,
                          ready=not blocker, missing=missing, cost=s.get("cost", ""), note=s.get("note", ""),
                          blocker=blocker))
    return out


def ready_platforms(cfg: dict, env: dict | None = None) -> list[str]:
    return [s.platform for s in status(cfg, env) if s.ready]


# ---------------------------------------------------------------- budget

class Budget:
    """Month-by-month spend on paid platforms, in US dollars."""

    def __init__(self, path: Path = SOCIAL_DATA_DIR / "spend.json"):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    @staticmethod
    def month(now: datetime | None = None) -> str:
        return (now or datetime.now(timezone.utc)).strftime("%Y-%m")

    def spent(self, platform: str, now: datetime | None = None) -> float:
        return float(self.data.get(self.month(now), {}).get(platform, 0.0))

    def allow(self, platform: str, amount: float, limit: float, now: datetime | None = None) -> bool:
        return self.spent(platform, now) + amount <= limit + 1e-9

    def add(self, platform: str, amount: float, now: datetime | None = None) -> None:
        m = self.data.setdefault(self.month(now), {})
        m[platform] = round(float(m.get(platform, 0.0)) + amount, 4)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class OverBudget(RuntimeError):
    pass


def charge(cfg: dict, platform: str, requests: int, budget: Budget | None) -> None:
    """Check and record the cost of `requests` calls. Raises OverBudget when the limit would be passed."""
    s = cfg.get(platform, {})
    price = float(s.get("cost_per_request_usd", 0.0))
    if not price or budget is None:
        return
    amount = price * requests
    limit = float(s.get("monthly_budget_usd", 0.0))
    if not budget.allow(platform, amount, limit):
        raise OverBudget(f"{platform}: monthly budget of ${limit:.2f} reached "
                         f"(spent ${budget.spent(platform):.2f})")
    budget.add(platform, amount)


# ---------------------------------------------------------------- collecting

def _adapter(platform: str):
    if platform == "bluesky":
        from . import bluesky as m
    elif platform == "youtube":
        from . import youtube as m
    elif platform == "x":
        from . import x as m
    elif platform == "reddit":
        from . import reddit as m
    else:
        raise ValueError(f"no adapter for {platform}")
    return m


def collect(cfg: dict, region: str, day: date, env: dict | None = None, http: Http | None = None,
            budget: Budget | None = None, data_dir: Path = SOCIAL_DATA_DIR) -> dict[str, str]:
    """Count yesterday's posts on every ready platform. Returns a short report per platform."""
    env = os.environ if env is None else env
    http = http or Http()
    report = {}
    for p in ready_platforms(cfg, env):
        settings = cfg[p]
        region_settings = settings.get(region)
        if not region_settings:
            report[p] = f"no settings for region '{region}'"
            continue
        m = _adapter(p)
        try:
            charge(cfg, p, m.requests_per_day(settings, region_settings), budget)
            rows = m.count_rows(settings, region_settings, day, env, http)
        except OverBudget as e:
            report[p] = str(e)
            continue
        except Exception as e:  # one platform failing never stops the others
            report[p] = f"failed: {e}"
            continue
        save_rows(history_file(region, p, data_dir), rows)
        total = sum(r[2] for r in rows if r[0] == day.isoformat())
        capped = any(r[3] for r in rows)
        report[p] = f"{len(rows)} rows, {total} posts on {day.isoformat()}" + (" (some terms capped)" if capped else "")
    return report


def history_file(region: str, platform: str, data_dir: Path = SOCIAL_DATA_DIR) -> Path:
    return data_dir / region / f"{platform}.csv"


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


def save_rows(path: Path, rows: list[tuple]) -> None:
    """Upsert (date, term, count, capped) rows into the platform's history file."""
    existing = {(r["date"], r["term"]): r for r in load_rows(path)}
    for d, term, count, capped in rows:
        existing[(d, term)] = {"date": d, "term": term, "count": int(count), "capped": int(bool(capped))}
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(sorted(existing.values(), key=lambda r: (r["date"], r["term"])))
    path.write_text(buf.getvalue(), encoding="utf-8")


def daily_totals(path: Path) -> Series:
    totals: dict[str, float] = defaultdict(float)
    for r in load_rows(path):
        totals[r["date"]] += float(r["count"])
    return sorted(totals.items())


def pulse_signals(cfg: dict, region: str, data_dir: Path = SOCIAL_DATA_DIR) -> list[tuple[PulseSignal, Series]]:
    """Extra pulse signals from platforms that are switched on and have stored counts."""
    out = []
    for p in PLATFORMS:
        s = cfg.get(p, {})
        if not (s.get("enabled") and s.get("available", True)):
            continue
        path = history_file(region, p, data_dir)
        if not path.exists():
            continue
        label = s.get("label", p.title())
        sig = PulseSignal(id=f"social_{p}", name=f"Money-worry posts on {label}", lens="household",
                          direction=-1, weight=float(s.get("weight", 0.5)), source=f"{label} official API")
        out.append((sig, daily_totals(path)))
    return out


def x_alert_watch(cfg: dict, region: str, env: dict | None = None) -> dict | None:
    """The hourly X watch, when X is ready and hourly_alerts is switched on."""
    s = cfg.get("x", {})
    if "x" not in ready_platforms(cfg, env) or not s.get("hourly_alerts") or not s.get(region, {}).get("query"):
        return None
    return {"id": "x_money_worry", "name": "Money-worry posts on X",
            "fetch": {"kind": "x_counts", "query": s[region]["query"]}}

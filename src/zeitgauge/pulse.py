"""The daily pulse: fast public signals, read every morning.

The monthly verdict (scoring.py) uses official statistics against long-run
normals, so it is stable and slow. The pulse asks a narrower question each day:
is this week better or worse than the last four months?

Method, per signal (see docs/pulse.md):
  1. Take the last `recent_days` values (default 7) and average them.
  2. Build the baseline from the `baseline_days` before that: every 7-day
     average in that window. Their median is "usual" and their MAD (scaled to
     match a standard deviation) is the typical swing. Median and MAD ignore
     one-off spikes, which daily data is full of.
  3. score = direction * (this week - usual) / swing, capped at +/-2.5.
     change = the same for this week against last week.
The scores are then combined into one test statistic, asking how unlikely
this week's mix of readings would be if nothing had changed:

  combined = sum(weight * score) / (sqrt(sum(weight^2)) * NULL_Z_SD)
  index    = 50 + 10 * combined, kept between 0 and 100

50 means "same as the last four months". 65 or more (combined 1.5) is better
than ordinary week-to-week noise would give on about 19 days in 20, so it reads
as improving; 35 or less reads as worsening. One loud signal on its own rarely
gets there; several pointing the same way do. NULL_Z_SD is calibrated by
simulation (tests/test_pulse.py checks it) because a week's average compared
with four months of overlapping weekly averages wobbles a little more than a
textbook z-score.

The pulse is a leading read and is never folded into the monthly verdict.
It earns trust the same way everything else does: through scored forecasts.
"""

from __future__ import annotations

import csv
import io
import math
import statistics
import tomllib
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from .config import ROOT
from .fetchers import Series
from .scoring import clip

PULSE_CONFIG_DIR = ROOT / "config" / "pulse"
PULSE_DATA_DIR = ROOT / "data" / "pulse"
IMPROVING_AT = 65
WORSENING_AT = 35
NULL_Z_SD = 1.2  # spread of a signal's score when nothing has changed (see module docstring)
NOTABLE_DAY_Z = 3.0
STALE_AFTER_DAYS = 10
MAD_TO_SD = 1.4826


@dataclass(frozen=True)
class PulseSignal:
    id: str
    name: str
    lens: str
    direction: int
    weight: float = 1.0
    source: str = ""
    enabled: bool = True
    fetch: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PulseConfig:
    region: str
    recent_days: int
    baseline_days: int
    min_baseline: int
    signals: tuple[PulseSignal, ...]
    alerts: dict = field(default_factory=dict)


def load_pulse(region_id: str, config_dir: Path = PULSE_CONFIG_DIR) -> PulseConfig:
    raw = tomllib.loads((config_dir / f"{region_id}.toml").read_text(encoding="utf-8"))
    p = raw.get("pulse", {})
    signals = tuple(
        PulseSignal(id=s["id"], name=s["name"], lens=s.get("lens", "household"),
                    direction=int(s["direction"]), weight=float(s.get("weight", 1.0)),
                    source=s.get("source", ""), enabled=bool(s.get("enabled", True)),
                    fetch=dict(s.get("fetch", {})))
        for s in raw.get("signals", [])
    )
    for s in signals:
        if s.direction not in (-1, 1):
            raise ValueError(f"pulse {region_id}:{s.id} direction must be +1 or -1")
    return PulseConfig(region=p.get("region", region_id), recent_days=int(p.get("recent_days", 7)),
                       baseline_days=int(p.get("baseline_days", 120)),
                       min_baseline=int(p.get("min_baseline", 30)), signals=signals,
                       alerts=dict(raw.get("alerts", {})))


# ---------------------------------------------------------------- statistics

def robust_centre_scale(values: list[float]) -> tuple[float, float]:
    """Median and a robust swing (MAD scaled to a standard deviation, or SD if MAD is 0)."""
    centre = statistics.median(values)
    mad = statistics.median(abs(v - centre) for v in values) * MAD_TO_SD
    if mad > 0:
        return centre, mad
    return centre, statistics.pstdev(values) if len(values) > 1 else 0.0


def rolling_means(values: list[float], n: int) -> list[float]:
    if n <= 1:
        return list(values)
    out, total = [], sum(values[:n - 1])
    for i in range(n - 1, len(values)):
        total += values[i]
        out.append(total / n)
        total -= values[i - n + 1]
    return out


def score_series(series: Series, direction: int, recent_days: int = 7, baseline_days: int = 120,
                 min_baseline: int = 30) -> tuple[dict | None, str]:
    """Score one daily series. Returns (result, "") or (None, reason it was skipped)."""
    values = [v for _, v in series][-(baseline_days + recent_days):]
    if len(values) < recent_days + min_baseline:
        return None, f"building history ({len(values)} of {recent_days + min_baseline} days)"
    recent, base = values[-recent_days:], values[:-recent_days]
    usual, swing = robust_centre_scale(rolling_means(base, recent_days))
    if not swing:
        return None, "no variation in the baseline"
    now = statistics.fmean(recent)
    before = statistics.fmean(values[-2 * recent_days:-recent_days])
    day_centre, day_swing = robust_centre_scale(base)
    day_z = direction * (values[-1] - day_centre) / day_swing if day_swing else 0.0
    score = clip(direction * (now - usual) / swing)
    return {
        "this_week": round(now, 4), "usual": round(usual, 4), "swing": round(swing, 4),
        "score": round(score, 2), "change": round(clip(direction * (now - before) / swing), 2),
        "latest": values[-1], "day_z": round(day_z, 2), "notable_day": abs(day_z) >= NOTABLE_DAY_Z,
        "reading": "better than usual" if score >= 0.5 else "worse than usual" if score <= -0.5 else "usual",
    }, ""


# ---------------------------------------------------------------- the pulse

def mood_of(index: int) -> str:
    if index >= IMPROVING_AT:
        return "improving"
    if index <= WORSENING_AT:
        return "worsening"
    return "steady"


HEADLINES = {
    "improving": "Improving on the last four months",
    "worsening": "Worsening on the last four months",
    "steady": "Steady, in line with the last four months",
}


def early_read(mood: str, phase: str | None) -> str:
    """What today's pulse suggests about the next monthly verdict."""
    if mood == "steady" or phase is None:
        return "Nothing new since the monthly verdict." if phase else "No monthly verdict to compare with yet."
    table = {
        ("improving", "downturn"): "An early hint that the squeeze is easing. The official figures have yet to confirm it.",
        ("improving", "slowdown"): "An early hint that the slowdown is bottoming out. Watch the next official figures.",
        ("improving", "recovery"): "The recovery is gathering pace in the daily signals too.",
        ("improving", "expansion"): "Good times are still building.",
        ("worsening", "downturn"): "The squeeze is deepening. Expect the next official figures to stay weak.",
        ("worsening", "slowdown"): "The slowdown may be tipping into a downturn. Watch the next official figures.",
        ("worsening", "recovery"): "An early warning: the recovery is stalling in the daily signals.",
        ("worsening", "expansion"): "An early warning: daily signals are souring before the official figures.",
    }
    return table.get((mood, phase), "Nothing new since the monthly verdict.")


def _stale(series: Series, today: date) -> bool:
    try:
        last = date.fromisoformat(series[-1][0][:10])
    except (IndexError, ValueError):
        return True
    return (today - last).days > STALE_AFTER_DAYS


def score_pulse(cfg: PulseConfig, series_by_id: dict[str, Series], monthly: dict | None = None,
                today: date | None = None, extra_signals: tuple[PulseSignal, ...] = (),
                history: list[dict] | None = None) -> dict:
    today = today or date.today()
    signals = [s for s in cfg.signals if s.enabled] + list(extra_signals)
    used, skipped = [], []
    # per lens: [sum of weight*score, sum of weight*change, sum of weights, sum of weights squared]
    totals = {"all": [0.0, 0.0, 0.0, 0.0], "household": [0.0, 0.0, 0.0, 0.0], "society": [0.0, 0.0, 0.0, 0.0]}
    weight_all = sum(s.weight for s in signals) or 1.0
    for sig in signals:
        series = series_by_id.get(sig.id)
        if not series:
            skipped.append({"id": sig.id, "name": sig.name, "reason": "no data this run"})
            continue
        if _stale(series, today):
            skipped.append({"id": sig.id, "name": sig.name, "reason": f"stale (last {series[-1][0]})"})
            continue
        res, why = score_series(series, sig.direction, cfg.recent_days, cfg.baseline_days, cfg.min_baseline)
        if res is None:
            skipped.append({"id": sig.id, "name": sig.name, "reason": why})
            continue
        used.append({"id": sig.id, "name": sig.name, "lens": sig.lens, "source": sig.source,
                     "weight": sig.weight, "latest_date": series[-1][0], **res})
        for key in ("all", sig.lens):
            if key in totals:
                totals[key][0] += res["score"] * sig.weight
                totals[key][1] += res["change"] * sig.weight
                totals[key][2] += sig.weight
                totals[key][3] += sig.weight ** 2

    def combined(key: str) -> float | None:
        s, _, w, w2 = totals[key]
        return s / (math.sqrt(w2) * NULL_Z_SD) if w else None

    def idx(key: str) -> int | None:
        c = combined(key)
        return None if c is None else max(0, min(100, round(50 + 10 * c)))

    w_used = totals["all"][2]
    coverage = round(w_used / weight_all, 2)
    out = {"region": cfg.region, "date": today.isoformat(), "coverage": coverage,
           "signals": used, "skipped": skipped,
           "notable": [u["name"] for u in used if u["notable_day"]]}
    if not used or coverage < 0.5:
        out.update({"index": None, "mood": "unknown",
                    "headline": "Not enough daily data yet",
                    "early_read": "Fewer than half the daily signals came through. Check the skipped list."})
        return out
    index = idx("all")
    mood = mood_of(index)
    phase = (monthly or {}).get("phase")
    out.update({
        "index": index, "household_index": idx("household"), "society_index": idx("society"),
        "combined": round(combined("all"), 2),
        "level": round(totals["all"][0] / w_used, 3), "momentum": round(totals["all"][1] / w_used, 3),
        "mood": mood, "headline": HEADLINES[mood], "early_read": early_read(mood, phase),
        "monthly": None if not monthly else {k: monthly.get(k) for k in ("phase", "headline", "as_of")},
        "streak": streak(history or [], mood, today),
    })
    return out


def streak(history: list[dict], mood: str, today: date) -> int:
    """Days in a row (including today) with the same mood."""
    n = 1
    for row in sorted((r for r in history if r.get("date", "") < today.isoformat()),
                      key=lambda r: r["date"], reverse=True):
        if row.get("mood") != mood:
            break
        n += 1
    return n


# ---------------------------------------------------------------- fetching

def fetch_signal(spec: dict) -> Series:
    kind = spec.get("kind")
    if kind == "epu":
        from .fetchers.epu import UK_DAILY, fetch_epu_daily
        return fetch_epu_daily(spec.get("url", UK_DAILY))
    if kind == "gdelt":
        from .fetchers.gdelt import fetch_gdelt
        return fetch_gdelt(spec["query"], spec.get("mode", "timelinetone"), spec.get("timespan", "150d"))
    if kind == "wikipedia":
        from .fetchers.wikipedia import fetch_pageviews
        return fetch_pageviews(spec["articles"], days=int(spec.get("days", 150)),
                               project=spec.get("project", "en.wikipedia"))
    if kind == "fred":
        from .fetchers.fred import fetch_fred
        return fetch_fred(spec["series"])
    if kind == "boe":
        from .fetchers.boe import fetch_boe
        return fetch_boe(spec["series"], start_year=date.today().year - 1)
    if kind == "trends":
        from .fetchers.trends import interest_over_time
        df = interest_over_time(spec["keywords"], geo=spec.get("geo", "GB"),
                                timeframe=spec.get("timeframe", "today 3-m"))
        cols = [c for c in spec["keywords"] if c in df.columns]
        return [(str(ix)[:10], float(sum(row[c] for c in cols))) for ix, row in df.iterrows()]
    raise ValueError(f"unknown pulse source kind: {kind}")


# ---------------------------------------------------------------- storage

HISTORY_FIELDS = ["date", "index", "household_index", "society_index", "momentum", "coverage", "mood"]


def history_path(region_id: str, data_dir: Path = PULSE_DATA_DIR) -> Path:
    return data_dir / region_id / "history.csv"


def load_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


def save_history(path: Path, history: list[dict], result: dict, keep_days: int = 800) -> list[dict]:
    rows = [r for r in history if r.get("date") != result["date"]]
    rows.append({k: "" if result.get(k) is None else result.get(k) for k in HISTORY_FIELDS})
    rows.sort(key=lambda r: r["date"])
    cutoff = (date.fromisoformat(result["date"]) - timedelta(days=keep_days)).isoformat()
    rows = [r for r in rows if r["date"] >= cutoff]
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=HISTORY_FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8")
    return rows

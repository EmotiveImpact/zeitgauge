"""Hourly alerts: tell someone when a topic suddenly jumps.

Each watch in config/pulse/<region>.toml is a news query (or, if switched on,
an X post count). Every hour we fetch the past week at hourly resolution and
compare the latest couple of hours with the rest of the week:

  usual  = median of the earlier points
  swing  = MAD scaled to a standard deviation
  fires when (now - usual) / swing >= z   AND   now / usual >= ratio

Both tests must pass, so a quiet topic doubling from 1 to 2 articles does not
fire, and nor does a busy topic wobbling within its normal range. After firing,
a watch stays quiet for `cooldown_hours`.

Alerts are saved to data/alerts/<region>/log.jsonl and web/alerts.json, and
can be pushed to a phone (ntfy), any webhook (Slack, Discord and similar) and
a GitHub issue. See docs/pulse.md.
"""

from __future__ import annotations

import json
import os
import statistics
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import ROOT
from .fetchers import Series, user_agent
from .pulse import robust_centre_scale

ALERT_DATA_DIR = ROOT / "data" / "alerts"
WEB_ALERTS = ROOT / "web" / "alerts.json"
MIN_BASELINE_POINTS = 24
KEEP_WEB = 30


def detect_spike(series: Series, recent_points: int = 2, z: float = 3.0, ratio: float = 2.0,
                 min_points: int = MIN_BASELINE_POINTS) -> dict | None:
    values = [v for _, v in series]
    if len(values) < min_points + recent_points:
        return None
    recent, base = values[-recent_points:], values[:-recent_points]
    usual, swing = robust_centre_scale(base)
    now = statistics.fmean(recent)
    z_now = (now - usual) / swing if swing else (float("inf") if now > usual else 0.0)
    r_now = now / usual if usual > 0 else (float("inf") if now > 0 else 0.0)
    return {"at": series[-1][0], "now": round(now, 4), "usual": round(usual, 4),
            "z": round(z_now, 2) if z_now != float("inf") else 99.0,
            "ratio": round(r_now, 2) if r_now != float("inf") else 99.0,
            "fired": z_now >= z and r_now >= ratio}


def _parse_time(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def check_watches(region: str, alert_cfg: dict, series_by_id: dict[str, Series], state: dict,
                  now: datetime | None = None, region_name: str | None = None) -> tuple[list[dict], dict]:
    """Return (new alerts, updated state). State maps watch id to the last time it fired."""
    now = now or datetime.now(timezone.utc)
    z = float(alert_cfg.get("z", 3.0))
    ratio = float(alert_cfg.get("ratio", 2.0))
    cooldown = timedelta(hours=float(alert_cfg.get("cooldown_hours", 12)))
    recent = int(alert_cfg.get("recent_points", 2))
    new_state = dict(state)
    fired = []
    for watch in alert_cfg.get("watch", []):
        series = series_by_id.get(watch["id"])
        if not series:
            continue
        res = detect_spike(series, recent_points=recent, z=z, ratio=ratio)
        if not res or not res["fired"]:
            continue
        last = state.get(watch["id"])
        if last and now - _parse_time(last) < cooldown:
            continue
        where = region_name or region.upper()
        what = "posts on X" if watch.get("fetch", {}).get("kind") == "x_counts" else f"{where} news coverage"
        times = "many" if res["ratio"] >= 99 else f"{res['ratio']:.1f}"
        fired.append({
            "region": region, "id": watch["id"], "name": watch["name"], "time": now.isoformat(timespec="minutes"),
            "data_time": res["at"], "ratio": res["ratio"], "z": res["z"], "now": res["now"], "usual": res["usual"],
            "message": f"{watch['name']}: {what} is running at {times} times its usual level for this week.",
        })
        new_state[watch["id"]] = now.isoformat(timespec="minutes")
    return fired, new_state


# ---------------------------------------------------------------- storage

def state_path(region: str, data_dir: Path = ALERT_DATA_DIR) -> Path:
    return data_dir / region / "state.json"


def load_state(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_log(region: str, alerts: list[dict], data_dir: Path = ALERT_DATA_DIR) -> None:
    if not alerts:
        return
    path = data_dir / region / "log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for a in alerts:
            f.write(json.dumps(a) + "\n")


def update_web(alerts: list[dict], path: Path = WEB_ALERTS) -> None:
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"alerts": []}
    merged = (alerts + existing.get("alerts", []))[:KEEP_WEB]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"updated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                                "alerts": merged}, indent=2) + "\n", encoding="utf-8")


def summary_markdown(alerts: list[dict]) -> str:
    lines = ["Zeitgauge spotted a sudden jump.", ""]
    for a in alerts:
        lines.append(f"- **{a['name']}** ({a['region'].upper()}): {a['message']} "
                     f"(z {a['z']}, data to {a['data_time']})")
    lines += ["", "Spikes are a prompt to look, not a verdict. The monthly reading only changes with official data."]
    return "\n".join(lines)


# ---------------------------------------------------------------- notifications

def _post(url: str, body: bytes, headers: dict) -> None:
    req = urllib.request.Request(url, data=body, method="POST", headers={"User-Agent": user_agent(), **headers})
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 (user-configured URL)
        resp.read()


def notify(alerts: list[dict], env: dict | None = None, post=_post) -> list[str]:
    """Send alerts to whichever channels are configured. Returns the channels used.

    NTFY_TOPIC         phone push through ntfy (free app). Pick a long random
                       topic name: anyone who knows it can read the messages.
    NTFY_SERVER        optional, defaults to https://ntfy.sh
    ALERT_WEBHOOK_URL  any webhook that takes JSON ("text" for Slack, "content" for Discord)
    """
    env = os.environ if env is None else env
    if not alerts:
        return []
    used = []
    text = "\n".join(a["message"] for a in alerts)
    topic = env.get("NTFY_TOPIC", "").strip()
    if topic:
        server = env.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
        title = "Zeitgauge alert" if len(alerts) == 1 else f"Zeitgauge: {len(alerts)} alerts"
        try:
            post(f"{server}/{topic}", text.encode("utf-8"),
                 {"Title": title, "Tags": "chart_with_upwards_trend", "Content-Type": "text/plain; charset=utf-8"})
            used.append("ntfy")
        except Exception as e:  # never let a notification failure stop the run
            print(f"  ntfy failed: {e}")
    hook = env.get("ALERT_WEBHOOK_URL", "").strip()
    if hook:
        try:
            post(hook, json.dumps({"text": text, "content": text, "alerts": alerts}).encode("utf-8"),
                 {"Content-Type": "application/json"})
            used.append("webhook")
        except Exception as e:
            print(f"  webhook failed: {e}")
    return used

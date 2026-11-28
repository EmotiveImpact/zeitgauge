"""Weekly brief: what people need right now, and what to build for it.

Each week Zeitgauge reads the monthly verdict, the daily pulse and the past
week's alerts, then scores every need in config/needs.toml:

  aligned  = -score if the need grows as a signal gets worse for households,
             +score if it grows as the signal gets better
  evidence = weighted mean of the aligned scores over the drivers this region
             has (daily pulse drivers count at half weight, being noisier)
  rank     = evidence, plus 0.5 if the need suits this phase or overlay,
             plus 0.25 if one of its alert watches fired this week

Confidence counts how many separate signals agree: Strong needs three or more
pointing firmly the same way. Every need put forward becomes a dated call
(basis "need:<id>") checked 13 weeks later against Google searches, so the
catalogue earns trust through its record (forecasting.brier_by). See
docs/brief.md.
"""

from __future__ import annotations

import json
import statistics
import tomllib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import ROOT
from .forecasting import Forecast, brier
from .playbook import NEXT_PHASE

NEEDS_FILE = ROOT / "config" / "needs.toml"
BRIEF_DATA_DIR = ROOT / "data" / "brief"
PULSE_DATA_DIR = ROOT / "data" / "pulse"
ALERT_DATA_DIR = ROOT / "data" / "alerts"

PULSE_FACTOR = 0.5  # daily drivers count at half weight
FIRM = 0.5  # an aligned score this big counts as a signal firmly backing the need
LIST_ABOVE = 0.25  # evidence needed to mention a need at all
FIT_BONUS = 0.5
ALERT_BONUS = 0.25
MIN_DRIVERS = 2
TOP_NEEDS = 3
IDEAS_PER_NEED = 2
PULSE_FRESH_DAYS = 8
ALERT_DAYS = 7
CALL_DAYS = 91  # 13 weeks
CHECK_WINDOW_DAYS = 28
PROBABILITY = {"Strong": 0.65, "Moderate": 0.6, "Early": 0.55}
GEO = {"uk": ("GB", "the UK"), "us": ("US", "the US")}
PHASE_WORDS = {"expansion": "expansion", "slowdown": "a slowdown", "downturn": "a downturn", "recovery": "recovery"}
TREND_WORDS = {"building": "still growing", "easing": "easing a little since last month", "holding": "holding steady"}
OVERLAY_WORDS = {"strained": "under strain", "stable": "steady"}


@dataclass(frozen=True)
class Driver:
    id: str
    source: str  # "monthly" or "pulse"
    when: str  # "worse" or "better"
    weight: float


@dataclass(frozen=True)
class Idea:
    name: str
    format: str = ""
    price: str = ""
    test: str = ""
    tech: str = ""


@dataclass(frozen=True)
class Need:
    id: str
    name: str
    feeling: str
    phases: tuple[str, ...]
    overlay: tuple[str, ...]
    drivers: tuple[Driver, ...]
    alerts: tuple[str, ...]
    searches: tuple[str, ...]
    ideas: tuple[Idea, ...]


def load_needs(path: Path = NEEDS_FILE) -> list[Need]:
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    needs, seen = [], set()
    for n in raw.get("needs", []):
        nid = n["id"]
        if nid in seen:
            raise ValueError(f"needs: duplicate id '{nid}'")
        seen.add(nid)
        drivers = []
        for d in n.get("drivers", []):
            if ("signal" in d) == ("pulse" in d):
                raise ValueError(f"{nid}: each driver needs exactly one of 'signal' or 'pulse'")
            when = d.get("when", "worse")
            if when not in ("worse", "better"):
                raise ValueError(f"{nid}: 'when' must be 'worse' or 'better', got '{when}'")
            weight = float(d.get("weight", 1.0))
            if weight <= 0:
                raise ValueError(f"{nid}: driver weights must be positive")
            drivers.append(Driver(id=d.get("signal") or d["pulse"], source="monthly" if "signal" in d else "pulse",
                                  when=when, weight=weight))
        ideas = tuple(Idea(name=i["name"], format=i.get("format", ""), price=i.get("price", ""),
                           test=i.get("test", ""), tech=i.get("tech", "")) for i in n.get("ideas", []))
        if not ideas:
            raise ValueError(f"{nid}: add at least one idea")
        needs.append(Need(id=nid, name=n["name"], feeling=n.get("feeling", ""),
                          phases=tuple(n.get("phases", [])), overlay=tuple(n.get("overlay", [])),
                          drivers=tuple(drivers), alerts=tuple(n.get("alerts", [])),
                          searches=tuple(n.get("check", {}).get("searches", [])), ideas=ideas))
    return needs


# ---------------------------------------------------------------- inputs

def load_pulse_latest(region: str, today: date, data_dir: Path | None = None) -> dict | None:
    """Today's pulse breakdown, if the daily job has written a recent one."""
    path = (data_dir or PULSE_DATA_DIR) / region / "latest.json"
    if not path.exists():
        return None
    pulse = json.loads(path.read_text(encoding="utf-8"))
    try:
        age = (today - date.fromisoformat(pulse.get("date", "")[:10])).days
    except ValueError:
        return None
    return pulse if age <= PULSE_FRESH_DAYS else None


def load_recent_alerts(region: str, today: date, data_dir: Path | None = None) -> list[dict]:
    path = (data_dir or ALERT_DATA_DIR) / region / "log.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        a = json.loads(line)
        try:
            day = datetime.fromisoformat(a["time"]).date()
        except (KeyError, ValueError):
            continue
        if 0 <= (today - day).days <= ALERT_DAYS:
            out.append(a)
    return out


# ---------------------------------------------------------------- wording

def fmt_value(value, unit: str = "") -> str:
    if value is None:
        return "n/a"
    text = f"{round(float(value), 2):g}"
    if unit in ("%", "x"):
        return text + unit
    return f"{text} {unit}" if unit else text


def nice_date(d: date) -> str:
    return f"{d.day} {d:%B %Y}"


def nice_iso(text: str | None) -> str:
    """'2026-11-26' as '26 November 2026'; anything else unchanged."""
    try:
        return nice_date(date.fromisoformat(str(text)[:10]))
    except ValueError:
        return str(text)


def _trend(m: float | None) -> str:
    if m is None:
        return ""
    if m >= 0.05:
        return "getting better"
    if m <= -0.05:
        return "getting worse"
    return "little changed"


def monthly_line(s: dict) -> str:
    unit = s.get("unit", "")
    trend = _trend(s.get("momentum"))
    tail = f"{s['band']}, {trend}" if trend else s["band"]
    return f"{s['name']}: {fmt_value(s['latest'], unit)} against a normal of {fmt_value(s['normal'], unit)} ({tail})"


def pulse_line(s: dict) -> str:
    change = s.get("change") or 0.0
    week = "better than last week" if change >= 0.5 else "worse than last week" if change <= -0.5 else "about the same as last week"
    return f"{s['name']}: {s.get('reading', 'usual')} this week, {week} (daily pulse)"


# ---------------------------------------------------------------- scoring

def _matches(d: Driver, monthly: dict[str, dict], pulse: dict[str, dict]) -> list[dict]:
    pool = monthly if d.source == "monthly" else pulse
    if d.id.endswith("*"):
        return [s for k, s in pool.items() if k.startswith(d.id[:-1])]
    return [pool[d.id]] if d.id in pool else []


def score_need(need: Need, monthly: dict[str, dict], pulse: dict[str, dict], phase: str, stability: str,
               alerts: list[dict] = ()) -> dict | None:
    """Score one need. Returns None when the region has too few of its drivers."""
    rows = []
    for d in need.drivers:
        for s in _matches(d, monthly, pulse):
            sign = -1.0 if d.when == "worse" else 1.0
            move = s.get("momentum") if d.source == "monthly" else s.get("change")
            rows.append({
                "id": s["id"], "name": s["name"], "source": d.source, "when": d.when,
                "weight": d.weight * (PULSE_FACTOR if d.source == "pulse" else 1.0),
                "aligned": sign * float(s["score"]),
                "aligned_change": None if move is None else sign * float(move),
                "line": monthly_line(s) if d.source == "monthly" else pulse_line(s),
            })
    if len(rows) < MIN_DRIVERS:
        return None

    def wmean(rs: list[dict], key: str) -> float | None:
        total = sum(r["weight"] for r in rs)
        return sum(r["weight"] * r[key] for r in rs) / total if total else None

    evidence = wmean(rows, "aligned")
    momentum = wmean([r for r in rows if r["aligned_change"] is not None], "aligned_change") or 0.0
    pulse_evidence = wmean([r for r in rows if r["source"] == "pulse"], "aligned")
    backing = sorted((r for r in rows if r["aligned"] >= FIRM), key=lambda r: -r["weight"] * r["aligned"])
    against = sorted((r for r in rows if r["aligned"] <= -FIRM), key=lambda r: r["weight"] * r["aligned"])
    fit = phase in need.phases or stability in need.overlay
    fired = [a for a in alerts if a.get("id") in need.alerts]
    if len(backing) >= 3 and evidence >= 0.75:
        confidence = "Strong"
    elif len(backing) >= 2 and evidence >= 0.4:
        confidence = "Moderate"
    else:
        confidence = "Early"
    trend = "building" if momentum >= 0.1 else "easing" if momentum <= -0.1 else "holding"

    next_phase = NEXT_PHASE.get(phase, "")
    if need.phases:
        holds_next = next_phase in need.phases
        next_note = (f"Still works if the cycle turns to {next_phase}." if holds_next else
                     f"Likely to fade if the cycle turns to {next_phase}, so keep stock and fixed costs light.")
    else:
        holds_next = None
        moods = " or ".join(OVERLAY_WORDS.get(o, o) for o in need.overlay)
        next_note = f"Tied to the social mood more than the economy, so it lasts while society stays {moods}."

    turn_better = [r["name"] for r in backing if r["when"] == "worse"][:2]
    turn_worse = [r["name"] for r in backing if r["when"] == "better"][:2]
    weaken = []
    if turn_better:
        weaken.append("these turn better for households: " + ", ".join(turn_better))
    if turn_worse:
        weaken.append("these turn worse for households: " + ", ".join(turn_worse))

    return {
        "id": need.id, "name": need.name, "feeling": need.feeling,
        "rank": round(evidence + (FIT_BONUS if fit else 0.0) + (ALERT_BONUS if fired else 0.0), 3),
        "evidence": round(evidence, 3), "momentum": round(momentum, 3), "trend": trend,
        "pulse_evidence": None if pulse_evidence is None else round(pulse_evidence, 3),
        "rising_this_week": pulse_evidence is not None and pulse_evidence >= FIRM,
        "confidence": confidence, "fit": fit, "drivers_found": len(rows),
        "why": [r["line"] for r in backing[:4]],
        "against": [r["line"] for r in against[:2]],
        "alerts": [{"message": a["message"], "time": a.get("time", "")} for a in fired],
        "holds_next": holds_next, "next_note": next_note,
        "weaken": "; or ".join(weaken),
    }


def pick_ideas(need: Need, tech_wave: str | None, n: int = IDEAS_PER_NEED) -> list[dict]:
    """Ideas that ride the current technology wave go first, then catalogue order."""
    ranked = sorted(enumerate(need.ideas), key=lambda t: (0 if tech_wave and t[1].tech == tech_wave else 1, t[0]))
    return [{"name": i.name, "format": i.format, "price": i.price, "test": i.test,
             "rides_tech_wave": bool(tech_wave and i.tech == tech_wave)} for _, i in ranked[:n]]


def build_brief(report: dict, needs: list[Need], pulse: dict | None = None, alerts: list[dict] = (),
                today: date | None = None, calls: list[Forecast] = ()) -> dict:
    today = today or date.today()
    region = report["region"]
    phase, stability = report["phase"], report["stability"]
    monthly = {s["id"]: s for s in report["household"]["signals"] + report["society"]["signals"]}
    pulse_sigs = {s["id"]: s for s in (pulse or {}).get("signals", [])}
    tech = report.get("playbook", {}).get("tech_wave")
    tech_wave = None
    if tech:
        from .playbook import TECH_WAVE
        tech_wave = next((k for k, (name, _) in TECH_WAVE.items() if name == tech.get("phase")), None)

    by_id = {n.id: n for n in needs}
    scored = [s for n in needs if (s := score_need(n, monthly, pulse_sigs, phase, stability, list(alerts)))]
    listed = sorted((s for s in scored if s["evidence"] > LIST_ABOVE), key=lambda s: -s["rank"])
    top, also = listed[:TOP_NEEDS], listed[TOP_NEEDS:]

    geo, where = GEO.get(region, (region.upper(), region.upper()))
    open_calls = {f.basis: f for f in calls if f.region == region and f.outcome is None}
    for s in top:
        need = by_id[s["id"]]
        s["ideas"] = pick_ideas(need, tech_wave)
        due = today + timedelta(days=CALL_DAYS)
        existing = open_calls.get(f"need:{s['id']}")
        if existing:
            s["call"] = {"status": "open", "id": existing.id, "made_on": existing.made_on,
                         "due": existing.resolves_by, "probability": existing.probability,
                         "question": existing.question}
        elif need.searches:
            terms = " and ".join(f"'{t}'" for t in need.searches)
            s["call"] = {
                "status": "proposed", "id": f"{region}-brief-{today.isoformat()}-{need.id}",
                "made_on": today.isoformat(), "due": due.isoformat(), "probability": PROBABILITY[s["confidence"]],
                "question": (f"Google searches in {where} for {terms} are higher in the 4 weeks to "
                             f"{nice_date(due)} than in the same 4 weeks a year earlier"),
                "check": {"kind": "trends", "geo": geo, "keywords": list(need.searches),
                          "window_days": CHECK_WINDOW_DAYS},
            }

    worlds = sorted(report.get("scenarios", {}).get("worlds", []),
                    key=lambda w: (-(w["lit"] / w["known"]) if w.get("known") else 0, -w.get("lit", 0)))
    movers = sorted((s for s in pulse_sigs.values() if abs(s.get("change") or 0) >= 0.5),
                    key=lambda s: -abs(s["change"]))
    need_calls = [f for f in calls if f.basis.startswith("need:")]
    resolved = [f for f in need_calls if f.outcome is not None]
    open_dues = sorted(f.resolves_by for f in need_calls if f.outcome is None)

    return {
        "region": region, "region_name": report.get("region_name", region.upper()),
        "date": today.isoformat(), "week_of": (today - timedelta(days=today.weekday())).isoformat(),
        "monthly": {"as_of": report.get("as_of"), "phase": phase, "stability": stability,
                    "headline": report.get("headline"), "levelling_off": report.get("levelling_off", False),
                    "household_index": report["household"]["index"], "society_index": report["society"]["index"],
                    "household_momentum": report["household"]["momentum"],
                    "next_phase": NEXT_PHASE.get(phase), "readings_file": report.get("readings_file")},
        "tech_wave": tech,
        "pulse": None if not pulse else {
            "date": pulse.get("date"), "index": pulse.get("index"), "mood": pulse.get("mood"),
            "headline": pulse.get("headline"), "early_read": pulse.get("early_read"),
            "streak": pulse.get("streak"), "signals": len(pulse_sigs),
            "movers": [{"name": s["name"], "change": s["change"]} for s in movers[:3]],
            "notable": pulse.get("notable", []),
        },
        "alerts": [{"name": a.get("name"), "message": a.get("message"), "time": a.get("time")} for a in alerts],
        "needs": top,
        "also": [{k: s[k] for k in ("id", "name", "feeling", "confidence", "evidence", "trend")}
                 | {"why": s["why"][:1]} for s in also],
        "scenarios": [{"name": w["name"], "lit": w["lit"], "known": w["known"], "story": w["story"]}
                      for w in worlds[:2]],
        "scorecard": {"settled": len(resolved), "right": sum(1 for f in resolved if f.outcome),
                      "brier": None if not resolved else round(brier(resolved), 3),
                      "open": len(open_dues), "next_due": open_dues[0] if open_dues else None},
        "checked": [],
        "method": "needs-v1",
    }


# ---------------------------------------------------------------- calls

def make_calls(brief: dict) -> list[Forecast]:
    """Turn the brief's proposed calls into forecasts for the log."""
    out = []
    for s in brief["needs"]:
        c = s.get("call")
        if not c or c["status"] != "proposed":
            continue
        out.append(Forecast(id=c["id"], question=c["question"], probability=c["probability"],
                            made_on=c["made_on"], resolves_by=c["due"], region=brief["region"],
                            basis=f"need:{s['id']}", check=c["check"]))
        c["status"] = "logged"
    return out


def trends_fetch(keywords: list[str], geo: str, start: date, end: date) -> list[tuple[str, float]]:
    from .fetchers.trends import interest_over_time
    df = interest_over_time(list(keywords), geo=geo, timeframe=f"{start:%Y-%m-%d} {end:%Y-%m-%d}")
    cols = [c for c in keywords if c in df.columns]
    return [(str(ix)[:10], float(sum(row[c] for c in cols))) for ix, row in df.iterrows()]


def resolve_calls(calls: list[Forecast], today: date, fetch=trends_fetch) -> list[dict]:
    """Settle need calls that have come due. One download covers both windows,
    because Google Trends values are only comparable within one request."""
    done = []
    for f in calls:
        if f.outcome is not None or not f.check or f.check.get("kind") != "trends":
            continue
        due = date.fromisoformat(f.resolves_by)
        if due > today:
            continue
        win = int(f.check.get("window_days", CHECK_WINDOW_DAYS))
        year_ago = due - timedelta(days=365)
        try:
            series = fetch(f.check["keywords"], f.check.get("geo", "GB"), year_ago - timedelta(days=win + 14), due)
        except Exception as e:  # Trends is unofficial and flaky: try again next week
            done.append({"id": f.id, "question": f.question, "result": f"could not check yet ({e})"})
            continue

        def window(end: date) -> list[float]:
            return [v for d, v in series if end - timedelta(days=win) < date.fromisoformat(d[:10]) <= end]

        recent, before = window(due), window(year_ago)
        if not recent or not before:
            done.append({"id": f.id, "question": f.question, "result": "not enough search data yet"})
            continue
        now, then = statistics.fmean(recent), statistics.fmean(before)
        f.outcome = now > then
        done.append({"id": f.id, "question": f.question, "outcome": f.outcome,
                     "result": f"{now:.0f} against {then:.0f} a year earlier, so {'right' if f.outcome else 'wrong'}"})
    return done


# ---------------------------------------------------------------- output

def render_markdown(b: dict) -> str:
    m, p = b["monthly"], b["pulse"]
    name = b["region_name"]
    lead = f"The {name}" if name.startswith(("United", "Netherlands", "Philippines")) else name
    lines = [f"# What people need right now: {name}", "",
             f"{nice_iso(b['date'])}. Monthly figures as of {nice_iso(m['as_of'])}."
             + (f" Daily pulse from {nice_iso(p['date'])}." if p else ""), ""]

    read = (f"{lead} is in {PHASE_WORDS.get(m['phase'], m['phase'])}"
            + (", levelling off," if m["levelling_off"] else "")
            + f" and society is {OVERLAY_WORDS.get(m['stability'], m['stability'])}. "
            f"Households score {m['household_index']} and society {m['society_index']}, where 50 is normal.")
    if p and p.get("index") is not None:
        read += f" The daily pulse reads {p['index']}: {p['headline'].lower()}. {p['early_read']}"
    else:
        read += " The daily pulse is still building its history, so this week leans on the monthly figures."
    names = [f"**{s['name'].lower()}**" for s in b["needs"]]
    if names:
        joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
        read += f" The strongest needs are {joined}."
    if b.get("tech_wave"):
        read += f" Technology is in its {b['tech_wave']['phase'].lower()}. {b['tech_wave']['advice']}"
    lines += ["## The read", "", read, ""]

    lines += ["## What moved this week", ""]
    hm = m.get("household_momentum") or 0.0
    lines.append("- Since last month, household signals are "
                 + ("improving." if hm >= 0.05 else "worsening." if hm <= -0.05 else "roughly flat."))
    if p:
        for mv in p["movers"]:
            lines.append(f"- {mv['name']}: {'better' if mv['change'] > 0 else 'worse'} than last week.")
        if not p["movers"]:
            lines.append("- No big moves in the daily signals.")
        if p.get("notable"):
            lines.append("- An unusual single day in: " + ", ".join(p["notable"]) + ".")
    else:
        lines.append("- The daily pulse joins once it has 37 days of data.")
    for a in b["alerts"]:
        lines.append(f"- Alert, {nice_iso(a['time'])}: {a['message']}")
    if not b["alerts"]:
        lines.append("- No news alerts fired.")
    lines.append("")

    lines += ["## Needs right now", ""]
    if not b["needs"]:
        lines += ["No need stands out clearly this week. Keep testing last week's ideas.", ""]
    for i, s in enumerate(b["needs"], 1):
        rising = " The daily signals are pushing it up this week." if s["rising_this_week"] else ""
        lines += [f"### {i}. {s['name']}", "",
                  f"{s['feeling']} Confidence: **{s['confidence']}**. The need is {TREND_WORDS[s['trend']]}.{rising}", "",
                  "**Why now**", ""]
        lines += [f"- {w}" for w in s["why"]] or ["- Several signals lean this way, none strongly."]
        lines += [f"- News alert: {a['message']}" for a in s["alerts"]]
        if s["against"]:
            lines += ["", "**Pulling the other way**", ""] + [f"- {w}" for w in s["against"]]
        lines += ["", "**What to build**", ""]
        for idea in s["ideas"]:
            extra = " Rides the current technology wave." if idea["rides_tech_wave"] else ""
            detail = ", ".join(x for x in (idea["format"], idea["price"]) if x)
            lines.append(f"- **{idea['name']}**" + (f" ({detail})" if detail else ""))
            if idea["test"]:
                lines.append(f"  - Test: {idea['test']}.")
            if extra:
                lines.append(f"  -{extra}")
        lines += ["", f"**If the cycle turns:** {s['next_note']}", ""]
        if s["weaken"]:
            lines += [f"**Would weaken if** {s['weaken']}.", ""]
        c = s.get("call")
        if c:
            pct = f"{round(c['probability'] * 100)}%"
            if c["status"] == "open":
                lines.append(f"**Scorecard:** already a call since {nice_iso(c['made_on'])}, "
                             f"checked on {nice_iso(c['due'])}.")
                lines.append("")
            else:
                verb = "Logged" if c["status"] == "logged" else "Proposed"
                lines.append(f"**Scorecard:** {verb} call at {pct}: {c['question']}.")
                lines.append("")
        if lines[-1] != "":
            lines.append("")

    if b["also"]:
        lines += ["## Also showing", ""]
        for s in b["also"]:
            why = f" Top signal: {s['why'][0]}." if s["why"] else ""
            lines.append(f"- **{s['name']}** ({s['confidence']}). {s['feeling']}{why}")
        lines.append("")

    lines += ["## Watch next", ""]
    for w in b["scenarios"][:1]:
        lines.append(f"- The scenario signposts point most to **{w['name']}** ({w['lit']} of {w['known']} lit). {w['story']}")
    nxt = m.get("next_phase")
    if nxt and b["needs"]:
        def join(xs: list[str]) -> str:
            return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]
        carry = [s["name"].lower() for s in b["needs"] if s["holds_next"] is True]
        fade = [s["name"].lower() for s in b["needs"] if s["holds_next"] is False]
        social = [s["name"].lower() for s in b["needs"] if s["holds_next"] is None]
        text = f"- The next phase in the cycle is {nxt}."
        if carry:
            text += f" {join(carry).capitalize()} {'still works' if len(carry) == 1 else 'still work'} then."
        if fade:
            text += f" {join(fade).capitalize()} {'tends' if len(fade) == 1 else 'tend'} to fade then, so test cheaply and avoid big stock."
        if social:
            text += f" {join(social).capitalize()} {'follows' if len(social) == 1 else 'follow'} the social mood instead."
        lines.append(text)
    lines.append("")

    sc = b["scorecard"]
    lines += ["## Scorecard", ""]
    for c in b["checked"]:
        lines.append(f"- Checked: {c['question']}. {c['result'].capitalize()}.")
    if sc["settled"]:
        lines.append(f"- Need calls settled so far: {sc['right']} right out of {sc['settled']}. "
                     f"Brier score {sc['brier']:.2f} (0 is perfect, 0.25 is a coin flip).")
    else:
        lines.append("- No need calls have come due yet."
                     + (f" The first is checked on {nice_iso(sc['next_due'])}." if sc["next_due"] else ""))
    lines.append("")

    lines += ["## How this was made", "",
              f"- Monthly figures: official statistics in `{m.get('readings_file')}`.",
              (f"- Daily pulse: {p['signals']} fast public signals, {nice_iso(p['date'])}." if p else
               "- Daily pulse: not available yet."),
              "- Each need is scored from the signals that drive it (`config/needs.toml`), with a bonus when it suits "
              "the current phase. Ideas are starting points to test cheaply. Every need put forward is checked 13 "
              "weeks later against Google searches, so the brief keeps score of itself.", ""]
    return "\n".join(lines)


def save_brief(b: dict, markdown: str, data_dir: Path | None = None) -> Path:
    folder = (data_dir or BRIEF_DATA_DIR) / b["region"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "latest.json").write_text(json.dumps(b, indent=2) + "\n", encoding="utf-8")
    (folder / "latest.md").write_text(markdown + "\n", encoding="utf-8")
    (folder / f"{b['date']}.md").write_text(markdown + "\n", encoding="utf-8")
    return folder

"""Command line entry point.

  python -m zeitgauge score --region uk        print the verdict and playbook
  python -m zeitgauge score --region uk --web  also write web/data.json
  python -m zeitgauge fetch --region uk        pull fresh official data
  python -m zeitgauge brier                    score past forecasts
  python -m zeitgauge pulse --region uk        the daily pulse from fast public signals
  python -m zeitgauge alerts --region uk       check for sudden spikes (run hourly)
  python -m zeitgauge social                   which social platforms are on, and their cost
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .config import READINGS_DIR, ROOT, load_readings, load_region, latest_readings_path
from .forecasting import brier, brier_by, load_log
from .playbook import playbook
from .scenarios import load_scenarios, signpost_status
from .scoring import score_region

WEB_DATA = ROOT / "web" / "data.json"
WEB_PULSE = ROOT / "web" / "pulse.json"
FORECAST_LOG = ROOT / "data" / "forecasts.json"


def build_report(region_id: str, readings_path: Path | None = None) -> dict:
    region = load_region(region_id)
    path = readings_path or latest_readings_path(region_id)
    doc = load_readings(path)
    verdict = score_region(region, doc)
    out = verdict.to_dict()
    out["region_name"] = region.name
    out["playbook"] = playbook(verdict.phase, verdict.stability, doc.get("tech_wave"))
    if region.narrative:
        out["narrative"] = {**region.narrative, "weight": 0}
    scenarios = load_scenarios(region_id)
    if scenarios:
        out["scenarios"] = signpost_status(verdict, scenarios)
    out["readings_file"] = str(Path(path).relative_to(ROOT)) if Path(path).is_relative_to(ROOT) else str(path)
    return out


def print_report(r: dict) -> None:
    print(f"\n{r['region_name']}  (data as of {r['as_of']})")
    print(f"  {r['headline']}")
    print(f"  Households index {r['household']['index']}  |  Society index {r['society']['index']}  (50 = normal)")
    print("\n  Design for:")
    for f in r["playbook"]["phase"] + r["playbook"]["overlay"]:
        print(f"   - {f['feeling']}: {f['why']} e.g. {f['examples']}")
    if "tech_wave" in r["playbook"]:
        tw = r["playbook"]["tech_wave"]
        print(f"\n  Technology wave: {tw['phase']}. {tw['advice']}")
    print(f"\n  Test ideas against the next phase too: {r['playbook']['next_phase']}")
    if "scenarios" in r:
        print("\n  Scenario signposts lit this month (pointers, not odds):")
        for w in r["scenarios"]["worlds"]:
            print(f"   - {w['name']}: {w['lit']} of {w['known']}. {w['story']}")
    if "narrative" in r:
        print(f"\n  Story lens ({r['narrative']['framework']}, weight 0): {r['narrative']['turning']}")
    print()


def cmd_score(args: argparse.Namespace) -> int:
    report = build_report(args.region, Path(args.readings) if args.readings else None)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    if args.web:
        WEB_DATA.parent.mkdir(parents=True, exist_ok=True)
        existing = json.loads(WEB_DATA.read_text(encoding="utf-8")) if WEB_DATA.exists() else {}
        existing.setdefault("regions", {})[args.region] = report
        existing["generated"] = date.today().isoformat()
        WEB_DATA.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        print(f"Wrote {WEB_DATA.relative_to(ROOT)}")
    return 0


def _fetch_one(spec: dict):
    from .fetchers import year_on_year
    kind = spec.get("kind")
    if kind == "ons":
        from .fetchers.ons import fetch_ons
        series = fetch_ons(spec["path"])
    elif kind == "boe":
        from .fetchers.boe import fetch_boe
        series = fetch_boe(spec["series"])
    elif kind == "fred":
        from .fetchers.fred import fetch_fred
        series = fetch_fred(spec["series"])
    elif kind == "derived" and spec.get("method") == "sahm":
        from .fetchers.fred import fetch_fred
        from .indicators.sahm import sahm_series
        raw = fetch_fred(spec["from"])
        values = sahm_series([v for _, v in raw])
        series = list(zip([d for d, _ in raw][-len(values):], values))
    else:
        return None
    if spec.get("transform") == "yoy":
        series = year_on_year(series)
    return series


def cmd_fetch(args: argparse.Namespace) -> int:
    from .fetchers import latest_two
    region = load_region(args.region)
    try:
        prev_doc = load_readings(latest_readings_path(args.region))
    except FileNotFoundError:
        prev_doc = {"readings": {}}
    readings = dict(prev_doc.get("readings", {}))
    failed = []
    for sig in region.signals:
        if sig.fetch.get("kind") in (None, "manual"):
            continue
        try:
            series = _fetch_one(sig.fetch)
        except Exception as e:  # network or parse problem: keep the old value, report it
            failed.append(f"{sig.id}: {e}")
            continue
        if not series:
            failed.append(f"{sig.id}: no data returned")
            continue
        latest, previous, period = latest_two(series)
        readings[sig.id] = {"latest": latest, "previous": previous, "period": period,
                            "url": sig.source}
        print(f"  {sig.id:<20} {latest}  (previous {previous}, {period})")
    today = date.today()
    out = {"region": args.region, "as_of": today.isoformat(),
           "note": "Fetched automatically; manual signals carried over from the last file.",
           "tech_wave": prev_doc.get("tech_wave"), "readings": readings}
    path = READINGS_DIR / args.region / f"{today:%Y-%m}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        print(json.dumps(out, indent=2))
    else:
        path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")
    for f in failed:
        print(f"  could not fetch {f}", file=sys.stderr)
    return 1 if failed and not readings else 0


def cmd_brier(args: argparse.Namespace) -> int:
    log = load_log(Path(args.log))
    score = brier(log)
    open_ = sum(1 for f in log if f.outcome is None)
    if score is None:
        print(f"No resolved forecasts yet ({open_} open).")
    else:
        print(f"Brier score {score:.3f} over {len(log) - open_} resolved forecasts ({open_} open). "
              "0 is perfect, 0.25 is a coin flip.")
        for basis, r in brier_by(log).items():
            if r["brier"] is not None:
                print(f"  {basis:<16} {r['brier']:.3f}  ({r['resolved']} resolved)")
    return 0


# ---------------------------------------------------------------- daily pulse

def _region_name(region_id: str) -> str:
    try:
        return load_region(region_id).name
    except FileNotFoundError:
        return region_id.upper()


def print_pulse(r: dict, name: str) -> None:
    print(f"\n{name} pulse, {r['date']}")
    if r.get("index") is None:
        print(f"  {r['headline']}. {r['early_read']}")
    else:
        run = f" ({r['streak']} days running)" if r.get("streak", 1) > 1 else ""
        print(f"  {r['index']}  {r['headline']}{run}")
        print(f"  {r['early_read']}")
        print(f"  Households {r['household_index']}  |  Society {r['society_index']}  "
              f"(50 = same as the last four months)")
    for u in r["signals"]:
        print(f"   - {u['name']}: {u['reading']} (score {u['score']:+.2f}, change {u['change']:+.2f})")
    if r.get("notable"):
        print("  Unusual single day: " + ", ".join(r["notable"]))
    for sk in r["skipped"]:
        print(f"   . skipped {sk['name']}: {sk['reason']}")
    for pr in r.get("problems", []):
        print(f"   ! {pr}", file=sys.stderr)
    print()


def cmd_pulse(args: argparse.Namespace) -> int:
    from . import social
    from .pulse import PULSE_DATA_DIR, fetch_signal, history_path, load_history, load_pulse, save_history, score_pulse
    cfg = load_pulse(args.region)
    series, problems = {}, []
    for sig in cfg.signals:
        if not sig.enabled:
            continue
        try:
            series[sig.id] = fetch_signal(sig.fetch)
        except Exception as e:  # one source failing never stops the pulse
            problems.append(f"{sig.id}: {e}")
    extras = []
    for sig, s in social.pulse_signals(social.load_social(), args.region):
        extras.append(sig)
        series[sig.id] = s
    try:
        monthly = build_report(args.region)
    except FileNotFoundError:
        monthly = None
    hpath = history_path(args.region)
    history = load_history(hpath)
    result = score_pulse(cfg, series, monthly, extra_signals=tuple(extras), history=history)
    result["problems"] = problems
    print_pulse(result, _region_name(args.region))
    if args.dry_run:
        return 0
    latest = PULSE_DATA_DIR / args.region / "latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if result.get("index") is not None:
        save_history(hpath, history, result)
    if args.web:
        existing = json.loads(WEB_PULSE.read_text(encoding="utf-8")) if WEB_PULSE.exists() else {}
        existing.setdefault("regions", {})[args.region] = result
        existing["generated"] = result["date"]
        WEB_PULSE.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {latest.relative_to(ROOT)}" + (f" and {WEB_PULSE.relative_to(ROOT)}" if args.web else ""))
    return 0 if result["signals"] else 1


# ---------------------------------------------------------------- hourly alerts

def cmd_alerts(args: argparse.Namespace) -> int:
    from . import alerts as al
    from . import social
    from .pulse import fetch_signal, load_pulse
    cfg = load_pulse(args.region)
    acfg = dict(cfg.alerts)
    watches = list(acfg.get("watch", []))
    scfg = social.load_social()
    xw = social.x_alert_watch(scfg, args.region)
    if xw:
        watches.append(xw)
    acfg["watch"] = watches
    budget = social.Budget()
    series, problems = {}, []
    for w in watches:
        try:
            if w["fetch"].get("kind") == "x_counts":
                from .social.x import hourly_series
                social.charge(scfg, "x", 1, budget)
                series[w["id"]] = hourly_series(w["fetch"]["query"], os.environ, social.Http())
            else:
                series[w["id"]] = fetch_signal(w["fetch"])
        except Exception as e:
            problems.append(f"{w['id']}: {e}")
    now = datetime.now(timezone.utc)
    print(f"\nAlert check, {_region_name(args.region)}, {now:%Y-%m-%d %H:%M} UTC")
    for w in watches:
        res = al.detect_spike(series.get(w["id"], []), recent_points=int(acfg.get("recent_points", 2)),
                              z=float(acfg.get("z", 3.0)), ratio=float(acfg.get("ratio", 2.0)))
        if res:
            flag = "SPIKE" if res["fired"] else "ok"
            print(f"   {flag:<5} {w['name']}: {res['ratio']}x usual (z {res['z']})")
        else:
            print(f"   ..    {w['name']}: not enough data")
    for pr in problems:
        print(f"   ! {pr}", file=sys.stderr)
    spath = al.state_path(args.region)
    new, state = al.check_watches(args.region, acfg, series, al.load_state(spath), now=now,
                                  region_name=_region_name(args.region))
    if xw:
        budget.save()
    if not new:
        # Quiet on failure: a news API timing out for an hour is normal, and the
        # daily pulse run already fails loudly if sources stay down.
        print("  No new alerts.")
        return 0
    for a in new:
        print(f"  ALERT {a['message']}")
    if args.dry_run:
        return 0
    al.append_log(args.region, new)
    al.update_web(new)
    al.save_state(spath, state)
    if args.notify:
        used = al.notify(new)
        print("  Sent to: " + (", ".join(used) if used else "nothing (no NTFY_TOPIC or ALERT_WEBHOOK_URL set)"))
    if args.summary:
        Path(args.summary).write_text(al.summary_markdown(new) + "\n", encoding="utf-8")
    return 0


# ---------------------------------------------------------------- social switch

def cmd_social(args: argparse.Namespace) -> int:
    from . import social
    scfg = social.load_social()
    if not args.collect:
        print("\nSocial media signals (config/social.toml)")
        for st in social.status(scfg):
            state = "ON " if st.ready else "off"
            print(f"\n  [{state}] {st.label}: {st.blocker or 'collecting'}")
            print(f"        Cost: {st.cost}")
            if st.note:
                print(f"        Note: {st.note}")
        budget = social.Budget()
        spent = budget.spent("x")
        if spent:
            print(f"\n  X spend this month: ${spent:.2f} of ${float(scfg.get('x', {}).get('monthly_budget_usd', 0)):.2f}")
        print()
        return 0
    day = date.fromisoformat(args.day) if args.day else datetime.now(timezone.utc).date() - timedelta(days=1)
    budget = social.Budget()
    report = social.collect(scfg, args.region, day, budget=budget)
    budget.save()
    if not report:
        print("No social platforms are switched on. Run `zeitgauge social` to see why.")
    for platform, line in report.items():
        print(f"  {platform:<8} {line}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="zeitgauge", description="Read the mood of a region and suggest what to build.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("score", help="score a region from its latest readings")
    s.add_argument("--region", default="uk")
    s.add_argument("--readings", help="path to a readings JSON file (default: latest)")
    s.add_argument("--json", action="store_true", help="print JSON instead of text")
    s.add_argument("--web", action="store_true", help="write web/data.json for the dashboard")
    s.set_defaults(func=cmd_score)

    f = sub.add_parser("fetch", help="download fresh official data for a region")
    f.add_argument("--region", default="uk")
    f.add_argument("--dry-run", action="store_true")
    f.set_defaults(func=cmd_fetch)

    b = sub.add_parser("brier", help="score resolved forecasts")
    b.add_argument("--log", default=str(FORECAST_LOG))
    b.set_defaults(func=cmd_brier)

    pu = sub.add_parser("pulse", help="daily pulse from fast public signals")
    pu.add_argument("--region", default="uk")
    pu.add_argument("--web", action="store_true", help="also write web/pulse.json")
    pu.add_argument("--dry-run", action="store_true", help="print only, write nothing")
    pu.set_defaults(func=cmd_pulse)

    al = sub.add_parser("alerts", help="check the alert watches for sudden spikes")
    al.add_argument("--region", default="uk")
    al.add_argument("--notify", action="store_true", help="send new alerts to ntfy or a webhook")
    al.add_argument("--summary", help="write a Markdown summary of new alerts to this file")
    al.add_argument("--dry-run", action="store_true")
    al.set_defaults(func=cmd_alerts)

    so = sub.add_parser("social", help="show the social media switches, or collect counts")
    so.add_argument("--collect", action="store_true", help="count posts on every platform that is switched on")
    so.add_argument("--region", default="uk")
    so.add_argument("--day", help="day to count, YYYY-MM-DD (default: yesterday, UTC)")
    so.set_defaults(func=cmd_social)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

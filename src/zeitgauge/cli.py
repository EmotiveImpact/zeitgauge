"""Command line entry point.

  python -m zeitgauge score --region uk        print the verdict and playbook
  python -m zeitgauge score --region uk --web  also write web/data.json
  python -m zeitgauge fetch --region uk        pull fresh official data
  python -m zeitgauge brier                    score past forecasts
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from .config import READINGS_DIR, ROOT, load_readings, load_region, latest_readings_path
from .forecasting import brier, brier_by, load_log
from .playbook import playbook
from .scenarios import load_scenarios, signpost_status
from .scoring import score_region

WEB_DATA = ROOT / "web" / "data.json"
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

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

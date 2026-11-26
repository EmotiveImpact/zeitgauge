"""Scenarios and signposts (Peter Schwartz, The Art of the Long View).

Each region can have a config/scenarios/<region>.toml with four worlds built
from two critical uncertainties. Every world lists signposts: conditions on
signals Zeitgauge already scores. This module counts which signposts are lit
this month, so drift towards a world shows up as a number.

The share of lit signposts is a pointer for attention. It is deliberately
not called a probability (Schwartz warns against odds on whole scenarios).
Probabilistic calls live in data/forecasts.json, where they can be scored.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from .config import ROOT
from .scoring import Verdict

SCENARIO_DIR = ROOT / "config" / "scenarios"


def load_scenarios(region_id: str, scenario_dir: Path = SCENARIO_DIR) -> dict | None:
    path = scenario_dir / f"{region_id}.toml"
    if not path.exists():
        return None
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _value(verdict: Verdict, signal: str, field: str) -> float | None:
    if signal.startswith("lens:"):
        lens = getattr(verdict, signal.split(":", 1)[1])
        return getattr(lens, field)
    for lens in (verdict.household, verdict.society):
        for d in lens.detail:
            if d["id"] == signal:
                return d.get(field)
    return None


def signpost_status(verdict: Verdict, doc: dict) -> dict:
    worlds = []
    for scn in doc.get("scenario", []):
        posts = []
        for sp in scn.get("signposts", []):
            v = _value(verdict, sp["signal"], sp["field"])
            if v is None:
                lit = None
            elif "above" in sp:
                lit = v > sp["above"]
            else:
                lit = v < sp["below"]
            posts.append({"label": sp["label"], "lit": lit,
                          "value": None if v is None else round(v, 3)})
        known = [p for p in posts if p["lit"] is not None]
        lit_n = sum(1 for p in known if p["lit"])
        worlds.append({"id": scn["id"], "name": scn["name"], "story": scn["story"],
                       "leans_towards": scn.get("leans_towards"),
                       "lit": lit_n, "known": len(known), "signposts": posts})
    worlds.sort(key=lambda w: (w["lit"] / w["known"]) if w["known"] else 0, reverse=True)
    return {"meta": doc.get("meta", {}), "worlds": worlds}

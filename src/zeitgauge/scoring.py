"""Core Zeitgauge scoring.

Method (see docs/algorithm.md):
  1. Score each signal against its long-run normal, in units of its typical swing,
     flipped so positive always means better for households. Capped at +/-CAP.
  2. Momentum = change since the previous reading, in the same units.
  3. Weighted averages give a level and a momentum per lens.
  4. Household level and momentum place the region on a four-phase cycle clock
     (the idea behind the ONS and Eurostat business cycle clocks).
  5. Social stability decides the overlay (stable or strained).

This is a transparent composite index in the spirit of the OECD Composite
Leading Indicators. It is meant to be explainable first and refined later with
fitted models (dynamic factor models, regime switching) once history is stored.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import Region, Signal

CAP = 2.5
FLAT_MOMENTUM = 0.03  # below this, momentum reads as "levelling off"
STRAINED_BELOW = -0.25  # society level below this reads as "strained"


def clip(x: float, cap: float = CAP) -> float:
    return max(-cap, min(cap, x))


def signal_score(sig: Signal, latest: float) -> float:
    return clip(sig.direction * (latest - sig.normal) / sig.swing)


def signal_momentum(sig: Signal, latest: float, previous: float | None) -> float | None:
    if previous is None:
        return None
    return clip(sig.direction * (latest - previous) / sig.swing)


def band(score: float) -> str:
    if score <= -0.5:
        return "worse than normal"
    if score >= 0.5:
        return "better than normal"
    return "near normal"


@dataclass
class LensResult:
    level: float
    momentum: float
    index: int  # 50 = long-run normal, 30 = one swing worse, 70 = one swing better
    detail: list[dict]


def score_lens(signals: list[Signal], readings: dict) -> LensResult:
    lvl = lvl_w = mom = mom_w = 0.0
    detail = []
    for sig in signals:
        r = readings.get(sig.id)
        if not r or r.get("latest") is None:
            continue
        z = signal_score(sig, float(r["latest"]))
        m = signal_momentum(sig, float(r["latest"]),
                            None if r.get("previous") is None else float(r["previous"]))
        lvl += z * sig.weight
        lvl_w += sig.weight
        if m is not None:
            mom += m * sig.weight
            mom_w += sig.weight
        detail.append({"id": sig.id, "name": sig.name, "latest": r["latest"],
                       "previous": r.get("previous"), "normal": sig.normal,
                       "score": round(z, 2), "momentum": None if m is None else round(m, 2),
                       "band": band(z), "leading": sig.leading, "unit": sig.unit})
    level = lvl / lvl_w if lvl_w else 0.0
    momentum = mom / mom_w if mom_w else 0.0
    return LensResult(level=level, momentum=momentum, index=round(50 + 20 * level), detail=detail)


def phase_of(level: float, momentum: float) -> str:
    if level >= 0:
        return "expansion" if momentum >= 0 else "slowdown"
    return "recovery" if momentum >= 0 else "downturn"


@dataclass
class Verdict:
    region: str
    as_of: str
    phase: str
    levelling_off: bool
    stability: str  # "stable" or "strained"
    household: LensResult
    society: LensResult

    def headline(self) -> str:
        names = {"expansion": "Expansion", "slowdown": "Slowdown",
                 "downturn": "Downturn: the squeeze", "recovery": "Recovery"}
        text = names[self.phase]
        if self.levelling_off:
            text += " (levelling off)"
        if self.stability == "strained":
            text += ", society under strain"
        return text

    def to_dict(self) -> dict:
        return {
            "region": self.region, "as_of": self.as_of, "phase": self.phase,
            "headline": self.headline(), "levelling_off": self.levelling_off,
            "stability": self.stability,
            "household": {"index": self.household.index, "level": round(self.household.level, 3),
                          "momentum": round(self.household.momentum, 3), "signals": self.household.detail},
            "society": {"index": self.society.index, "level": round(self.society.level, 3),
                        "momentum": round(self.society.momentum, 3), "signals": self.society.detail},
        }


def score_region(region: Region, readings_doc: dict) -> Verdict:
    readings = readings_doc["readings"]
    hh = score_lens(region.lens("household"), readings)
    so = score_lens(region.lens("society"), readings)
    return Verdict(
        region=region.id,
        as_of=readings_doc.get("as_of", ""),
        phase=phase_of(hh.level, hh.momentum),
        levelling_off=abs(hh.momentum) < FLAT_MOMENTUM,
        stability="strained" if so.level < STRAINED_BELOW else "stable",
        household=hh,
        society=so,
    )

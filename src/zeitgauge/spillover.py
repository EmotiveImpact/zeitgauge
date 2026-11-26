"""How one region's mood spills into another.

Version 1 (this file): a transparent link matrix. Each link says how strongly
a change in region A's household level feeds into region B, through three
channels we can reason about:
  - money: interest rates, bond yields and markets move together
  - trade: exports, imports and prices
  - culture: trends, platforms and media (US trends often reach the UK
    with a lag of weeks to months)

Version 2 (roadmap): estimate the links from history with the
Diebold-Yilmaz connectedness index (variance decomposition of a VAR across
regions), and replace the hand-set weights below with fitted ones.

Meadows: regions are stocks of confidence linked by flows with delays. This
module only handles the size of the link; delays are carried as lag_months
so the dashboard can say when an effect is likely to arrive.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Link:
    source: str
    target: str
    money: float  # 0..1
    trade: float  # 0..1
    culture: float  # 0..1
    lag_months: int

    @property
    def strength(self) -> float:
        # Equal channel weights to start; refine once fitted.
        return (self.money + self.trade + self.culture) / 3


# First estimates, to be replaced by fitted values (docs/cross-region.md).
LINKS: tuple[Link, ...] = (
    Link("us", "uk", money=0.7, trade=0.3, culture=0.7, lag_months=3),
    Link("uk", "us", money=0.2, trade=0.1, culture=0.3, lag_months=6),
)


def spillover(levels: dict[str, float], changes: dict[str, float],
              links: tuple[Link, ...] = LINKS) -> dict[str, dict]:
    """Return each region's own level plus the pressure arriving from others.

    levels:  {region: household level now}
    changes: {region: household momentum now}
    """
    out = {r: {"own_level": lvl, "incoming": 0.0, "sources": []} for r, lvl in levels.items()}
    for link in links:
        if link.source not in changes or link.target not in out:
            continue
        pressure = link.strength * changes[link.source]
        out[link.target]["incoming"] += pressure
        out[link.target]["sources"].append(
            {"from": link.source, "pressure": round(pressure, 3), "arrives_in_months": link.lag_months})
    for r in out:
        out[r]["outlook_level"] = out[r]["own_level"] + out[r]["incoming"]
    return out

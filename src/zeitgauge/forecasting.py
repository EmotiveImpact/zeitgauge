"""Keep score of our calls (Tetlock, Superforecasting).

Every monthly verdict should come with a few probabilistic forecasts, for
example "UK enters 'recovery' phase by June 2027: 25%". When each resolves,
record the outcome. The Brier score (0 = perfect, 0.25 = coin-flip at 50%,
lower is better) tells us which signals and judgements deserve trust.

Each forecast can name its basis: the signal, framework or scenario that
motivated it (for example "gfk", "perez", "strauss-howe"). brier_by() then
scores each basis separately, so frameworks compete on their record rather
than on how persuasive they sound. A framework that keeps losing gets less
attention; one that keeps winning can earn a weight in the score.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Forecast:
    id: str
    question: str
    probability: float  # 0..1
    made_on: str
    resolves_by: str
    region: str
    outcome: bool | None = None  # None until resolved
    basis: str = ""  # signal, framework or scenario behind the call

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability must be between 0 and 1")


def brier(forecasts: list[Forecast]) -> float | None:
    done = [f for f in forecasts if f.outcome is not None]
    if not done:
        return None
    return sum((f.probability - float(f.outcome)) ** 2 for f in done) / len(done)


def brier_by(forecasts: list[Forecast], key: str = "basis") -> dict[str, dict]:
    """Brier score grouped by a field (basis, region, ...), with counts."""
    groups: dict[str, list[Forecast]] = {}
    for f in forecasts:
        groups.setdefault(getattr(f, key) or "(none)", []).append(f)
    out = {}
    for k, fs in sorted(groups.items()):
        resolved = [f for f in fs if f.outcome is not None]
        out[k] = {"brier": brier(fs), "resolved": len(resolved), "open": len(fs) - len(resolved)}
    return out


def base_rate(events: int, periods: int) -> float:
    """Outside view first: how often has this happened before?"""
    if periods <= 0:
        raise ValueError("periods must be positive")
    return events / periods


def load_log(path: Path) -> list[Forecast]:
    if not Path(path).exists():
        return []
    return [Forecast(**row) for row in json.loads(Path(path).read_text(encoding="utf-8"))]


def save_log(path: Path, forecasts: list[Forecast]) -> None:
    Path(path).write_text(json.dumps([asdict(f) for f in forecasts], indent=2), encoding="utf-8")

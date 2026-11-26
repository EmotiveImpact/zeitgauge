"""Rank product ideas.

Two views, both simple enough to explain:

1. Weighted score (0 to 100) from five 1-to-5 ratings:
   fit with today's phase 30%, still works in the next phase 25%,
   audience size 20%, fit with your skills 15%, low cost to test 10%.

2. Robust choice across scenarios (Schwartz scenario planning plus
   robust decision-making): rate each idea's payoff in every scenario,
   then rank by a blend of expected payoff and worst case. An idea that
   is good in the likely scenario and survivable in the others beats one
   that is brilliant in one world and useless in the rest.
"""

from __future__ import annotations

from dataclasses import dataclass

WEIGHTS = {"fit": 0.30, "robust": 0.25, "audience": 0.20, "skills": 0.15, "cost": 0.10}


@dataclass
class Idea:
    name: str
    fit: int
    robust: int
    audience: int
    skills: int
    cost: int  # 1 = cheap to test, 5 = expensive

    def __post_init__(self) -> None:
        for k in ("fit", "robust", "audience", "skills", "cost"):
            v = getattr(self, k)
            if not 1 <= v <= 5:
                raise ValueError(f"{self.name}: {k} must be 1 to 5, got {v}")

    def score(self) -> int:
        ws = (WEIGHTS["fit"] * self.fit + WEIGHTS["robust"] * self.robust
              + WEIGHTS["audience"] * self.audience + WEIGHTS["skills"] * self.skills
              + WEIGHTS["cost"] * (6 - self.cost))
        return round((ws - 1) / 4 * 100)


def rank(ideas: list[Idea]) -> list[tuple[int, Idea]]:
    return sorted(((i.score(), i) for i in ideas), key=lambda t: t[0], reverse=True)


def robust_rank(payoffs: dict[str, dict[str, float]], probabilities: dict[str, float],
                caution: float = 0.4) -> list[tuple[str, float, float, float]]:
    """Rank ideas across scenarios.

    payoffs: {idea: {scenario: payoff 0..10}}
    probabilities: {scenario: probability}, normalised here
    caution: 0 = pure expected value, 1 = pure worst case (maximin)
    Returns [(idea, blended, expected, worst)] best first.
    """
    total = sum(probabilities.values())
    if total <= 0:
        raise ValueError("probabilities must sum to more than zero")
    p = {k: v / total for k, v in probabilities.items()}
    out = []
    for idea, by_scn in payoffs.items():
        expected = sum(p[s] * by_scn.get(s, 0.0) for s in p)
        worst = min(by_scn.get(s, 0.0) for s in p)
        out.append((idea, (1 - caution) * expected + caution * worst, expected, worst))
    return sorted(out, key=lambda t: t[1], reverse=True)

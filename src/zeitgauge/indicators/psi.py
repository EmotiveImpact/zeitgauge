"""Political Stress Index, light version (after Peter Turchin and Jack Goldstone).

Turchin's structural-demographic theory says societies become unstable when
three pressures build together:

  1. Mass mobilisation potential: ordinary people's pay falls behind the
     economy, young adults are numerous and crowded into cities.
  2. Elite overproduction: more people compete for a fixed number of top
     positions (degrees outpacing graduate jobs, rising cost of politics).
  3. State fiscal distress: public debt is high and trust in the state is low.

The full index (Turchin, Ages of Discord, 2016) multiplies these terms.
This light version keeps the multiplication, which is the important idea
(pressures amplify each other rather than simply adding up), and uses inputs
that are free and published every year. Every input is a ratio to its own
long-run normal, so 1.0 means "normal" and the index itself is 1.0 in a
normal year. Above roughly 1.5 to 2.0 history suggests elevated risk of
unrest, but that threshold is a judgement to calibrate, not a law.

Inputs (each a ratio to normal):
  rel_wage       median pay divided by GDP per head (lower = more pressure)
  youth_share    share of adults aged 20 to 29
  urban_share    share living in cities
  elite_ratio    graduates per graduate-level job (or a proxy)
  debt_ratio     public debt to GDP
  distrust       1 / trust in government
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PSIInputs:
    rel_wage: float
    youth_share: float
    urban_share: float
    elite_ratio: float
    debt_ratio: float
    distrust: float

    def __post_init__(self) -> None:
        for k, v in self.__dict__.items():
            if v <= 0:
                raise ValueError(f"{k} must be a positive ratio to normal, got {v}")


def psi(x: PSIInputs) -> dict:
    mmp = (1 / x.rel_wage) * x.youth_share * x.urban_share
    emp = x.elite_ratio
    sfd = x.debt_ratio * x.distrust
    total = mmp * emp * sfd
    return {
        "mass_mobilisation": round(mmp, 3),
        "elite_competition": round(emp, 3),
        "state_strain": round(sfd, 3),
        "psi": round(total, 3),
        "reading": "elevated" if total >= 1.5 else "watch" if total >= 1.15 else "normal",
    }


def to_signal(total: float) -> float:
    """Map PSI onto the society lens scale (0 = normal, negative = strain).

    log2 keeps it symmetric: PSI 2.0 gives -1 (one swing worse), 0.5 gives +1.
    """
    from math import log2
    return -log2(total)

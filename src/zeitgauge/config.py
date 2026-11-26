"""Load region configs (TOML) and monthly readings (JSON)."""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config" / "regions"
READINGS_DIR = ROOT / "data" / "readings"


@dataclass(frozen=True)
class Signal:
    id: str
    lens: str  # "household" or "society"
    name: str
    normal: float
    swing: float
    direction: int  # +1 if higher is better for households, -1 if worse
    weight: float = 1.0
    leading: bool = False
    unit: str = ""
    source: str = ""
    fetch: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Region:
    id: str
    name: str
    signals: tuple[Signal, ...]
    narrative: dict = field(default_factory=dict)

    def lens(self, name: str) -> list[Signal]:
        return [s for s in self.signals if s.lens == name]


def load_region(region_id: str, config_dir: Path = CONFIG_DIR) -> Region:
    raw = tomllib.loads((config_dir / f"{region_id}.toml").read_text(encoding="utf-8"))
    signals = tuple(
        Signal(
            id=s["id"],
            lens=s["lens"],
            name=s["name"],
            normal=float(s["normal"]),
            swing=float(s["swing"]),
            direction=int(s["direction"]),
            weight=float(s.get("weight", 1.0)),
            leading=bool(s.get("leading", False)),
            unit=s.get("unit", ""),
            source=s.get("source", ""),
            fetch=dict(s.get("fetch", {})),
        )
        for s in raw["signals"]
    )
    for s in signals:
        if s.swing <= 0:
            raise ValueError(f"{region_id}:{s.id} swing must be positive")
        if s.direction not in (-1, 1):
            raise ValueError(f"{region_id}:{s.id} direction must be +1 or -1")
    return Region(id=raw["region"]["id"], name=raw["region"]["name"], signals=signals,
                  narrative=dict(raw.get("narrative", {})))


def load_readings(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def latest_readings_path(region_id: str, readings_dir: Path = READINGS_DIR) -> Path:
    files = sorted((readings_dir / region_id).glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No readings for region '{region_id}' in {readings_dir}")
    return files[-1]

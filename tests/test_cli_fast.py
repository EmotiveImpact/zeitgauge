"""End-to-end runs of the pulse, alerts and social commands with the network swapped out."""

import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import zeitgauge.pulse as pulse_mod
from zeitgauge.cli import main
from zeitgauge.fetchers.gdelt import parse_gdelt_timeline

FX = Path(__file__).parent / "fixtures"


def fake_daily(spec):
    rnd = random.Random(str(spec))
    end = date.today() - timedelta(days=1)
    return [((end - timedelta(days=126 - i)).isoformat(), rnd.gauss(0, 1)) for i in range(127)]


def test_pulse_command_dry_run(monkeypatch, capsys):
    monkeypatch.setattr(pulse_mod, "fetch_signal", fake_daily)
    assert main(["pulse", "--region", "uk", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "United Kingdom pulse" in out and "(50 = same as the last four months)" in out
    assert "skipped Searches for help with money" not in out  # switched off, so not listed at all


def test_pulse_command_survives_a_dead_source(monkeypatch, capsys):
    def flaky(spec):
        if spec.get("kind") == "gdelt":
            raise OSError("timed out")
        return fake_daily(spec)
    monkeypatch.setattr(pulse_mod, "fetch_signal", flaky)
    assert main(["pulse", "--region", "uk", "--dry-run"]) == 0
    assert "timed out" in capsys.readouterr().err


def test_alerts_command_dry_run_spots_a_spike(monkeypatch, capsys):
    spike = parse_gdelt_timeline((FX / "gdelt_vol_hourly.json").read_text())
    calm = spike[:-2]
    monkeypatch.setattr(pulse_mod, "fetch_signal", lambda spec: spike if "redundancies" in spec["query"] else calm)
    assert main(["alerts", "--region", "uk", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "SPIKE Job cuts" in out and "ALERT Job cuts: United Kingdom news coverage" in out


def test_social_status_lists_every_platform(capsys):
    assert main(["social"]) == 0
    out = capsys.readouterr().out
    for name in ("Bluesky", "YouTube", "X", "Reddit", "TikTok"):
        assert f"] {name}:" in out
    assert "[ON " not in out

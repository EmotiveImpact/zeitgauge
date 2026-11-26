from zeitgauge.config import READINGS_DIR, Signal, load_readings, load_region
from zeitgauge.scoring import CAP, band, phase_of, score_lens, score_region, signal_score

NOV_2026 = READINGS_DIR / "uk" / "2026-11.json"


def sig(**kw):
    base = dict(id="x", lens="household", name="X", normal=0.0, swing=1.0, direction=1)
    base.update(kw)
    return Signal(**base)


def test_signal_score_flips_direction_and_caps():
    assert signal_score(sig(direction=-1), 1.0) == -1.0
    assert signal_score(sig(), 99) == CAP
    assert signal_score(sig(), -99) == -CAP


def test_phase_clock_quadrants():
    assert phase_of(0.5, 0.1) == "expansion"
    assert phase_of(0.5, -0.1) == "slowdown"
    assert phase_of(-0.5, -0.1) == "downturn"
    assert phase_of(-0.5, 0.1) == "recovery"


def test_band_edges():
    assert band(-0.5) == "worse than normal"
    assert band(0.49) == "near normal"
    assert band(0.5) == "better than normal"


def test_lens_skips_missing_and_weights_leading():
    sigs = [sig(id="a", weight=1.5), sig(id="b"), sig(id="c")]
    r = score_lens(sigs, {"a": {"latest": 1.0, "previous": 0.0}, "b": {"latest": -1.0}})
    assert round(r.level, 3) == round((1.5 - 1.0) / 2.5, 3)
    assert r.momentum == 1.0  # only 'a' has a previous reading
    assert len(r.detail) == 2


def test_uk_verdict_reproduces_dashboard():
    region = load_region("uk")
    v = score_region(region, load_readings(NOV_2026))
    assert v.phase == "downturn"
    assert v.stability == "strained"
    assert v.household.index == 36
    assert v.society.index == 33
    assert v.headline() == "Downturn: the squeeze, society under strain"


def test_us_config_loads_with_zero_weight_narrative():
    us = load_region("us")
    assert us.narrative["framework"] == "Strauss-Howe"
    assert {s.id for s in us.lens("household")} >= {"umich", "yield_curve", "sahm"}

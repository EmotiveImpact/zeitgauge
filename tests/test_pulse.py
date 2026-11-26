import json
import random
from datetime import date, timedelta
from pathlib import Path

import pytest

from zeitgauge.fetchers.epu import parse_epu_daily
from zeitgauge.fetchers.gdelt import gdelt_url, parse_gdelt_timeline
from zeitgauge.fetchers.wikipedia import pageviews_url, parse_pageviews
from zeitgauge.pulse import (
    PULSE_CONFIG_DIR, PulseConfig, PulseSignal, early_read, load_history, load_pulse, mood_of,
    robust_centre_scale, rolling_means, save_history, score_pulse, score_series,
)

FX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 11, 26)


def daily(values, end=TODAY - timedelta(days=1)):
    start = end - timedelta(days=len(values) - 1)
    return [((start + timedelta(days=i)).isoformat(), v) for i, v in enumerate(values)]


def noisy(n, centre=0.0, sd=1.0, seed=1):
    rnd = random.Random(seed)
    return [centre + rnd.gauss(0, sd) for _ in range(n)]


# ---------------------------------------------------------------- parsers

def test_parse_gdelt_daily_and_hourly_dates():
    tone = parse_gdelt_timeline((FX / "gdelt_tone_daily.json").read_text())
    assert len(tone) == 150
    assert tone[-1][0] == "2026-11-25"
    vol = parse_gdelt_timeline((FX / "gdelt_vol_hourly.json").read_text())
    assert vol[0][0] == "2026-11-19T10:00"
    assert vol[-1][1] == 0.47


def test_parse_gdelt_handles_empty_reply():
    assert parse_gdelt_timeline("") == []
    assert parse_gdelt_timeline("{}") == []


def test_gdelt_url_keeps_quotes_and_country():
    url = gdelt_url('("cost of living" OR redundancies) sourcecountry:UK', "timelinevol", "7d")
    assert "mode=timelinevol" in url and "timespan=7d" in url and "format=json" in url
    assert "%22cost%20of%20living%22" in url and "sourcecountry%3AUK" in url


def test_parse_pageviews_sums_articles_by_day():
    s = parse_pageviews((FX / "wiki_pageviews.json").read_text())
    assert s == [("2026-11-22", 5500.0), ("2026-11-23", 5700.0), ("2026-11-24", 5900.0)]


def test_pageviews_url_encodes_title():
    url = pageviews_url("Cost-of-living crisis", date(2026, 7, 1), date(2026, 11, 25))
    assert url.endswith("/en.wikipedia/all-access/user/Cost-of-living_crisis/daily/2026070100/2026112500")


def test_parse_epu_daily_real_rows():
    s = parse_epu_daily((FX / "epu_uk_daily.csv").read_text())
    assert s[0] == ("2026-11-19", 230.8)
    assert s[-1] == ("2026-11-25", 153.73)


# ---------------------------------------------------------------- statistics

def test_rolling_means():
    assert rolling_means([1, 2, 3, 4, 5], 2) == [1.5, 2.5, 3.5, 4.5]
    assert rolling_means([1, 2], 1) == [1, 2]


def test_robust_centre_ignores_one_wild_day():
    centre, swing = robust_centre_scale([10, 11, 9, 10, 12, 8, 10, 500])
    assert centre == 10
    assert swing < 3


def test_score_series_reads_direction():
    values = noisy(120) + [3.0] * 7
    up, _ = score_series(daily(values), direction=1)
    down, _ = score_series(daily(values), direction=-1)
    assert up["score"] >= 2.0 and up["reading"] == "better than usual"
    assert down["score"] <= -2.0 and down["reading"] == "worse than usual"
    assert up["notable_day"]


def test_score_series_needs_enough_history():
    res, why = score_series(daily(noisy(20)), direction=1)
    assert res is None and "building history (20 of 37 days)" in why


def test_score_series_flat_baseline_is_skipped():
    res, why = score_series(daily([5.0] * 60), direction=1)
    assert res is None and "no variation" in why


# ---------------------------------------------------------------- the pulse

def cfg_two():
    return PulseConfig(region="uk", recent_days=7, baseline_days=120, min_baseline=30, signals=(
        PulseSignal("tone", "News tone", "household", 1, 1.0),
        PulseSignal("epu", "Uncertainty", "society", -1, 1.0),
    ))


def test_pulse_improving_in_a_downturn_hints_at_a_turn():
    series = {"tone": daily(noisy(120, seed=2) + [2.0] * 7),
              "epu": daily(noisy(120, seed=3) + [-2.0] * 7)}
    r = score_pulse(cfg_two(), series, monthly={"phase": "downturn", "headline": "Downturn", "as_of": "2026-11-26"},
                    today=TODAY)
    assert r["index"] >= 75 and r["mood"] == "improving"
    assert r["household_index"] >= 65 and r["society_index"] >= 65
    assert "squeeze is easing" in r["early_read"]
    assert r["coverage"] == 1.0 and r["streak"] == 1


def test_pulse_worsening_and_steady():
    worse = score_pulse(cfg_two(), {"tone": daily(noisy(120, seed=4) + [-2.0] * 7),
                                    "epu": daily(noisy(120, seed=5) + [2.0] * 7)},
                        monthly={"phase": "expansion"}, today=TODAY)
    assert worse["mood"] == "worsening" and "early warning" in worse["early_read"]
    calm = score_pulse(cfg_two(), {"tone": daily(noisy(127, seed=6)), "epu": daily(noisy(127, seed=7))},
                       monthly={"phase": "downturn"}, today=TODAY)
    assert calm["mood"] == "steady" and calm["early_read"] == "Nothing new since the monthly verdict."


def test_pulse_skips_stale_and_missing_signals():
    old = daily(noisy(127), end=TODAY - timedelta(days=30))
    r = score_pulse(cfg_two(), {"tone": old}, today=TODAY)
    reasons = {s["id"]: s["reason"] for s in r["skipped"]}
    assert reasons["tone"].startswith("stale") and reasons["epu"] == "no data this run"
    assert r["index"] is None and r["mood"] == "unknown"


def test_pulse_needs_half_the_weight():
    cfg = PulseConfig(region="uk", recent_days=7, baseline_days=120, min_baseline=30, signals=(
        PulseSignal("a", "A", "household", 1, 1.0), PulseSignal("b", "B", "household", 1, 3.0)))
    r = score_pulse(cfg, {"a": daily(noisy(127))}, today=TODAY)
    assert r["coverage"] == 0.25 and r["index"] is None


def test_extra_signals_join_the_pulse():
    extra = PulseSignal("social_x", "Money-worry posts on X", "household", -1, 0.5)
    series = {"tone": daily(noisy(127, seed=8)), "epu": daily(noisy(127, seed=9)),
              "social_x": daily(noisy(120, 100, 10, seed=10) + [200.0] * 7)}
    r = score_pulse(cfg_two(), series, today=TODAY, extra_signals=(extra,))
    assert "social_x" in [s["id"] for s in r["signals"]]


def test_ordinary_noise_mostly_reads_steady():
    """Calibration check for NULL_Z_SD: with seven signals and nothing changing,
    the pulse should call a move on roughly one day in ten or fewer."""
    signals = tuple(PulseSignal(f"s{i}", f"S{i}", "household", 1, 1.0) for i in range(7))
    cfg = PulseConfig(region="uk", recent_days=7, baseline_days=120, min_baseline=30, signals=signals)
    moods = []
    for trial in range(150):
        series = {f"s{i}": daily(noisy(127, seed=1000 * trial + i)) for i in range(7)}
        moods.append(score_pulse(cfg, series, today=TODAY)["mood"])
    assert moods.count("steady") / len(moods) >= 0.8


def test_one_loud_signal_alone_is_not_a_trend():
    signals = tuple(PulseSignal(f"s{i}", f"S{i}", "household", 1, 1.0) for i in range(7))
    cfg = PulseConfig(region="uk", recent_days=7, baseline_days=120, min_baseline=30, signals=signals)
    series = {f"s{i}": daily([0.0, 0.1] * 60 + [0.05] * 7) for i in range(1, 7)}
    series["s0"] = daily(noisy(120, seed=11) + [5.0] * 7)
    assert score_pulse(cfg, series, today=TODAY)["mood"] == "steady"


def test_mood_thresholds_and_early_read_without_monthly():
    assert mood_of(65) == "improving" and mood_of(35) == "worsening" and mood_of(60) == "steady"
    assert early_read("improving", None) == "No monthly verdict to compare with yet."


def test_history_upserts_and_counts_streak(tmp_path):
    path = tmp_path / "history.csv"
    rows = []
    for i, mood in enumerate(["worsening", "improving", "improving"]):
        rows = save_history(path, rows, {"date": f"2026-11-2{i}", "index": 60, "household_index": 60,
                                         "society_index": 60, "momentum": 0.1, "coverage": 1.0, "mood": mood})
    rows = save_history(path, load_history(path), {"date": "2026-11-22", "index": 61, "household_index": 61,
                                                   "society_index": 61, "momentum": 0.1, "coverage": 1.0,
                                                   "mood": "improving"})
    assert [r["date"] for r in rows] == ["2026-11-20", "2026-11-21", "2026-11-22"]
    assert load_history(path)[-1]["index"] == "61"
    series = {"tone": daily(noisy(120, seed=2) + [2.0] * 7), "epu": daily(noisy(120, seed=3) + [-2.0] * 7)}
    r = score_pulse(cfg_two(), series, today=date(2026, 11, 23), history=load_history(path))
    assert r["streak"] == 3


@pytest.mark.parametrize("region", ["uk", "us"])
def test_pulse_configs_load(region):
    cfg = load_pulse(region)
    assert cfg.signals and cfg.alerts["watch"]
    kinds = {"epu", "gdelt", "wikipedia", "fred", "boe", "trends"}
    assert all(s.fetch["kind"] in kinds for s in cfg.signals)
    assert all(s.lens in ("household", "society") for s in cfg.signals)
    assert len({w["id"] for w in cfg.alerts["watch"]}) == len(cfg.alerts["watch"])
    assert (PULSE_CONFIG_DIR / f"{region}.toml").exists()

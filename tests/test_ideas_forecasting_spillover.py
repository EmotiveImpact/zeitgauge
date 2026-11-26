import pytest

from zeitgauge.forecasting import Forecast, base_rate, brier, brier_by, load_log, save_log
from zeitgauge.ideas import Idea, rank, robust_rank
from zeitgauge.playbook import playbook
from zeitgauge.spillover import Link, spillover


def test_idea_score_range():
    assert Idea("best", 5, 5, 5, 5, 1).score() == 100
    assert Idea("worst", 1, 1, 1, 1, 5).score() == 0
    with pytest.raises(ValueError):
        Idea("bad", 6, 1, 1, 1, 1)


def test_rank_orders_best_first():
    ranked = rank([Idea("a", 2, 2, 2, 2, 3), Idea("b", 5, 4, 4, 3, 2)])
    assert ranked[0][1].name == "b"


def test_robust_rank_prefers_survivable_idea():
    payoffs = {"one-trick": {"squeeze": 10, "boom": 0},
               "all-rounder": {"squeeze": 7, "boom": 6}}
    probs = {"squeeze": 0.6, "boom": 0.4}
    best = robust_rank(payoffs, probs, caution=0.4)[0]
    assert best[0] == "all-rounder"
    assert robust_rank(payoffs, probs, caution=0.0)[0][0] == "all-rounder"
    assert robust_rank(payoffs, {"squeeze": 1, "boom": 0}, caution=0.0)[0][0] == "one-trick"


def test_brier_and_base_rate(tmp_path):
    fs = [Forecast("1", "q", 0.8, "2026-11", "2027-06", "uk", True),
          Forecast("2", "q", 0.3, "2026-11", "2027-06", "uk", False),
          Forecast("3", "q", 0.5, "2026-11", "2027-06", "uk")]
    assert brier(fs) == pytest.approx((0.04 + 0.09) / 2)
    assert base_rate(3, 12) == 0.25
    p = tmp_path / "log.json"
    save_log(p, fs)
    assert load_log(p) == fs
    with pytest.raises(ValueError):
        Forecast("x", "q", 1.2, "", "", "uk")


def test_spillover_adds_pressure_with_lag():
    links = (Link("us", "uk", money=0.6, trade=0.3, culture=0.9, lag_months=3),)
    out = spillover({"uk": -0.7, "us": 0.2}, {"us": -0.3, "uk": 0.05}, links)
    assert out["uk"]["incoming"] == pytest.approx(-0.18)
    assert out["uk"]["sources"][0]["arrives_in_months"] == 3
    assert out["us"]["incoming"] == 0.0


def test_playbook_shapes():
    pb = playbook("downturn", "strained", "install")
    assert pb["next_phase"] == "recovery"
    assert len(pb["phase"]) == 3 and len(pb["overlay"]) == 2
    assert "tech_wave" in pb


def test_brier_by_basis_lets_frameworks_compete():
    fs = [Forecast("1", "q", 0.9, "", "", "us", True, basis="turchin"),
          Forecast("2", "q", 0.9, "", "", "us", False, basis="strauss-howe"),
          Forecast("3", "q", 0.5, "", "", "us", None, basis="strauss-howe")]
    by = brier_by(fs)
    assert by["turchin"]["brier"] == pytest.approx(0.01)
    assert by["strauss-howe"]["brier"] == pytest.approx(0.81)
    assert by["strauss-howe"]["open"] == 1

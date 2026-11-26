from zeitgauge.config import READINGS_DIR, load_readings, load_region
from zeitgauge.scenarios import load_scenarios, signpost_status
from zeitgauge.scoring import score_region

NOV_2026 = READINGS_DIR / "uk" / "2026-11.json"


def test_uk_scenarios_have_four_worlds_and_rank_by_signposts():
    v = score_region(load_region("uk"), load_readings(NOV_2026))
    status = signpost_status(v, load_scenarios("uk"))
    worlds = status["worlds"]
    assert len(worlds) == 4
    assert worlds[0]["id"] == "frayed"
    assert all(w["known"] == len(w["signposts"]) for w in worlds)


def test_missing_scenarios_file_returns_none():
    assert load_scenarios("nowhere") is None

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from zeitgauge.alerts import (
    append_log, check_watches, detect_spike, load_state, notify, save_state, summary_markdown, update_web,
)
from zeitgauge.fetchers.gdelt import parse_gdelt_timeline

FX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 11, 26, 10, 17, tzinfo=timezone.utc)
CFG = {"z": 3.0, "ratio": 2.0, "cooldown_hours": 12, "recent_points": 2,
       "watch": [{"id": "layoffs", "name": "Job cuts", "fetch": {"kind": "gdelt"}}]}


def hourly(values):
    t0 = datetime(2026, 11, 19, 10)
    return [((t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M"), v) for i, v in enumerate(values)]


def test_spike_in_saved_gdelt_reply_fires():
    s = parse_gdelt_timeline((FX / "gdelt_vol_hourly.json").read_text())
    res = detect_spike(s)
    assert res["fired"] and res["ratio"] > 3 and res["z"] > 3


def test_normal_wobble_does_not_fire():
    s = parse_gdelt_timeline((FX / "gdelt_vol_hourly.json").read_text())[:-2]
    assert not detect_spike(s)["fired"]


def test_quiet_topic_doubling_needs_both_tests():
    values = [1, 2, 1, 0, 1, 2, 1, 1, 0, 2] * 5 + [2, 2]
    res = detect_spike(hourly(values))
    assert res["ratio"] == 2.0 and not res["fired"]


def test_too_little_data_returns_none():
    assert detect_spike(hourly([1.0] * 10)) is None


def test_cooldown_blocks_repeat_alerts():
    s = parse_gdelt_timeline((FX / "gdelt_vol_hourly.json").read_text())
    new, state = check_watches("uk", CFG, {"layoffs": s}, {}, now=NOW, region_name="UK")
    assert len(new) == 1 and "UK news coverage" in new[0]["message"] and state["layoffs"] == "2026-11-26T10:17+00:00"
    again, _ = check_watches("uk", CFG, {"layoffs": s}, state, now=NOW + timedelta(hours=3))
    assert again == []
    later, _ = check_watches("uk", CFG, {"layoffs": s}, state, now=NOW + timedelta(hours=13))
    assert len(later) == 1


def test_x_watch_wording():
    cfg = dict(CFG, watch=[{"id": "x", "name": "Money-worry posts on X", "fetch": {"kind": "x_counts"}}])
    s = parse_gdelt_timeline((FX / "gdelt_vol_hourly.json").read_text())
    new, _ = check_watches("uk", cfg, {"x": s}, {}, now=NOW)
    assert "posts on X is running at" in new[0]["message"]


def test_storage_round_trip(tmp_path):
    alert = {"region": "uk", "id": "layoffs", "name": "Job cuts", "time": "t", "data_time": "d",
             "ratio": 3.4, "z": 9.1, "now": 1, "usual": 0.3, "message": "Job cuts: up."}
    save_state(tmp_path / "uk" / "state.json", {"layoffs": "t"})
    assert load_state(tmp_path / "uk" / "state.json") == {"layoffs": "t"}
    append_log("uk", [alert], data_dir=tmp_path)
    append_log("uk", [alert], data_dir=tmp_path)
    assert len((tmp_path / "uk" / "log.jsonl").read_text().splitlines()) == 2
    web = tmp_path / "alerts.json"
    update_web([alert], path=web)
    update_web([alert], path=web)
    assert len(json.loads(web.read_text())["alerts"]) == 2


def test_notify_uses_configured_channels_only():
    sent = []
    alert = {"message": "Job cuts: up.", "region": "uk", "name": "Job cuts", "z": 9, "data_time": "d"}
    assert notify([alert], env={}, post=lambda *a: sent.append(a)) == []
    used = notify([alert], env={"NTFY_TOPIC": "zg-abc123", "ALERT_WEBHOOK_URL": "https://example.com/hook"},
                  post=lambda url, body, headers: sent.append((url, body, headers)))
    assert used == ["ntfy", "webhook"]
    assert sent[0][0] == "https://ntfy.sh/zg-abc123" and sent[0][1] == b"Job cuts: up."
    assert json.loads(sent[1][1])["text"] == "Job cuts: up."


def test_notify_failure_does_not_raise():
    def boom(*a):
        raise OSError("offline")
    assert notify([{"message": "x"}], env={"NTFY_TOPIC": "t"}, post=boom) == []


def test_summary_markdown():
    md = summary_markdown([{"name": "Job cuts", "region": "uk", "message": "Job cuts: up.", "z": 9, "data_time": "d"}])
    assert "**Job cuts** (UK)" in md and "prompt to look" in md

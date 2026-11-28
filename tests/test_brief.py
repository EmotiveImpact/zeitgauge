"""The weekly 'what people need right now' brief."""

import json
import tomllib
from datetime import date, timedelta
from pathlib import Path

import pytest

import zeitgauge.brief as br
from zeitgauge.cli import build_report, main
from zeitgauge.config import ROOT
from zeitgauge.forecasting import Forecast, load_log, save_log

UK_NOV = ROOT / "data" / "readings" / "uk" / "2026-11.json"
TODAY = date(2026, 11, 30)


def uk_report():
    return build_report("uk", readings_path=UK_NOV)


def sig(id_, score, momentum=None, name=None, unit=""):
    return {"id": id_, "name": name or id_, "latest": 1.0, "normal": 0.0, "score": score,
            "momentum": momentum, "band": "worse than normal" if score <= -0.5 else "near normal", "unit": unit}


def need(**kw):
    base = dict(id="n", name="N", feeling="", phases=("downturn",), overlay=(), alerts=(), searches=("a", "b"),
                ideas=(br.Idea("one"), br.Idea("two", tech="install"), br.Idea("three")),
                drivers=(br.Driver("x", "monthly", "worse", 1.0), br.Driver("y", "monthly", "worse", 1.0),
                         br.Driver("z", "monthly", "better", 1.0)))
    base.update(kw)
    return br.Need(**base)


# ---------------------------------------------------------------- the catalogue

def test_catalogue_loads_and_every_id_exists_somewhere():
    needs = br.load_needs()
    assert len(needs) >= 10
    monthly, pulse, watches = set(), {"social_*"}, set()
    for region in ("uk", "us"):
        monthly |= {s["id"] for s in tomllib.loads((ROOT / "config/regions" / f"{region}.toml").read_text())["signals"]}
        cfg = tomllib.loads((ROOT / "config/pulse" / f"{region}.toml").read_text())
        pulse |= {s["id"] for s in cfg["signals"]}
        watches |= {w["id"] for w in cfg["alerts"]["watch"]}
    for n in needs:
        for d in n.drivers:
            assert d.id in (monthly if d.source == "monthly" else pulse), f"{n.id}: unknown {d.source} id {d.id}"
        for a in n.alerts:
            assert a in watches, f"{n.id}: unknown alert watch {a}"
        assert n.searches, f"{n.id}: needs searches so its calls can be checked"
        assert n.phases or n.overlay, f"{n.id}: say where it fits the playbook"


def test_catalogue_rejects_bad_drivers(tmp_path):
    p = tmp_path / "needs.toml"
    p.write_text('[[needs]]\nid="a"\nname="A"\nideas=[{name="x"}]\ndrivers=[{signal="gfk", pulse="epu"}]\n')
    with pytest.raises(ValueError, match="exactly one"):
        br.load_needs(p)
    p.write_text('[[needs]]\nid="a"\nname="A"\nideas=[{name="x"}]\ndrivers=[{signal="gfk", when="sideways"}]\n')
    with pytest.raises(ValueError, match="worse"):
        br.load_needs(p)
    p.write_text('[[needs]]\nid="a"\nname="A"\ndrivers=[{signal="gfk"}]\n')
    with pytest.raises(ValueError, match="idea"):
        br.load_needs(p)


# ---------------------------------------------------------------- scoring one need

def test_bad_signals_raise_a_worse_need_and_good_signals_lower_it():
    monthly = {"x": sig("x", -1.0), "y": sig("y", -1.0), "z": sig("z", -1.0)}
    r = br.score_need(need(), monthly, {}, "downturn", "stable")
    # x and y are bad (need grows), z is bad but the need wants it good (need shrinks)
    assert r["evidence"] == pytest.approx((1 + 1 - 1) / 3, abs=1e-3)
    assert len(r["why"]) == 2 and len(r["against"]) == 1
    assert r["fit"] and r["rank"] == pytest.approx(r["evidence"] + br.FIT_BONUS, abs=1e-3)


def test_confidence_needs_several_signals_agreeing():
    strong = {"x": sig("x", -1.5), "y": sig("y", -1.0), "z": sig("z", 1.0)}
    assert br.score_need(need(), strong, {}, "downturn", "stable")["confidence"] == "Strong"
    one_loud = {"x": sig("x", -2.5), "y": sig("y", 0.0), "z": sig("z", 0.0)}
    r = br.score_need(need(), one_loud, {}, "downturn", "stable")
    assert r["confidence"] == "Early" and r["evidence"] > br.LIST_ABOVE


def test_too_few_drivers_means_no_score():
    assert br.score_need(need(), {"x": sig("x", -2.0)}, {}, "downturn", "stable") is None


def test_pulse_counts_at_half_weight_and_flags_a_rising_need():
    n = need(drivers=(br.Driver("x", "monthly", "worse", 1.0), br.Driver("news", "pulse", "worse", 1.0)))
    pulse = {"news": {"id": "news", "name": "News", "score": -2.0, "change": -1.0, "reading": "worse than usual"}}
    r = br.score_need(n, {"x": sig("x", 0.0)}, pulse, "downturn", "stable")
    assert r["evidence"] == pytest.approx(2.0 * 0.5 / 1.5, abs=1e-3)
    assert r["rising_this_week"]
    assert any("daily pulse" in w for w in r["why"])


def test_wildcard_driver_picks_up_every_social_platform():
    n = need(drivers=(br.Driver("x", "monthly", "worse", 1.0), br.Driver("social_*", "pulse", "worse", 1.0)))
    pulse = {f"social_{p}": {"id": f"social_{p}", "name": p, "score": -1.0, "change": 0.0} for p in ("bluesky", "x")}
    assert br.score_need(n, {"x": sig("x", -1.0)}, pulse, "downturn", "stable")["drivers_found"] == 3


def test_an_alert_this_week_adds_a_bonus_and_a_reason():
    n = need(alerts=("prices",))
    monthly = {"x": sig("x", -1.0), "y": sig("y", -1.0), "z": sig("z", 0.0)}
    alert = {"id": "prices", "message": "Price shocks: news coverage is running at 3.0 times", "time": "2026-11-29T10:17"}
    with_alert = br.score_need(n, monthly, {}, "downturn", "stable", [alert])
    without = br.score_need(n, monthly, {}, "downturn", "stable", [])
    assert with_alert["rank"] == pytest.approx(without["rank"] + br.ALERT_BONUS, abs=1e-3)
    assert with_alert["alerts"][0]["message"].startswith("Price shocks")


def test_next_phase_note():
    monthly = {"x": sig("x", -1.0), "y": sig("y", -1.0), "z": sig("z", 0.0)}
    assert br.score_need(need(phases=("downturn", "recovery")), monthly, {}, "downturn", "stable")["holds_next"] is True
    assert br.score_need(need(), monthly, {}, "downturn", "stable")["holds_next"] is False
    social = br.score_need(need(phases=(), overlay=("strained",)), monthly, {}, "downturn", "strained")
    assert social["holds_next"] is None and "under strain" in social["next_note"]


def test_ideas_riding_the_tech_wave_go_first():
    assert [i["name"] for i in br.pick_ideas(need(), "install")] == ["two", "one"]
    assert [i["name"] for i in br.pick_ideas(need(), None)] == ["one", "two"]


# ---------------------------------------------------------------- the whole brief

def test_uk_november_brief_suits_a_downturn_under_strain():
    b = br.build_brief(uk_report(), br.load_needs(), today=TODAY)
    ids = [n["id"] for n in b["needs"]]
    assert len(ids) == br.TOP_NEEDS
    listed = ids + [a["id"] for a in b["also"]]
    for gone in ("treat_again", "getting_out", "time_saved", "status_novelty"):
        assert gone not in listed  # recovery and boom needs have no support in a squeeze
    for n in b["needs"]:
        assert n["why"] and len(n["ideas"]) == br.IDEAS_PER_NEED
        assert n["call"]["status"] == "proposed" and n["call"]["due"] == "2027-03-01"
    assert b["week_of"] == "2026-11-30" and b["pulse"] is None


def test_markdown_is_phone_friendly():
    b = br.build_brief(uk_report(), br.load_needs(), today=TODAY)
    md = br.render_markdown(b)
    assert md.startswith("# What people need right now: United Kingdom")
    for heading in ("## The read", "## Needs right now", "## Watch next", "## Scorecard"):
        assert heading in md
    assert "\u2014" not in md and "|" not in md  # no em dashes, no wide tables


def test_brief_uses_a_fresh_pulse_and_recent_alerts(tmp_path):
    pulse = {"date": "2026-11-29", "index": 30, "mood": "worsening", "headline": "Worsening on the last four months",
             "early_read": "The squeeze is deepening.", "streak": 3, "notable": [],
             "signals": [{"id": "news_squeeze", "name": "Share of UK news about the squeeze", "score": -2.5,
                          "change": -1.2, "reading": "worse than usual"}]}
    (tmp_path / "pulse" / "uk").mkdir(parents=True)
    (tmp_path / "pulse" / "uk" / "latest.json").write_text(json.dumps(pulse))
    (tmp_path / "alerts" / "uk").mkdir(parents=True)
    old = {"id": "prices", "name": "Price shocks", "message": "old", "time": "2026-11-01T10:17+00:00"}
    new = {"id": "prices", "name": "Price shocks", "message": "Price shocks: up", "time": "2026-11-28T10:17+00:00"}
    (tmp_path / "alerts" / "uk" / "log.jsonl").write_text(json.dumps(old) + "\n" + json.dumps(new) + "\n")
    p = br.load_pulse_latest("uk", TODAY, tmp_path / "pulse")
    alerts = br.load_recent_alerts("uk", TODAY, tmp_path / "alerts")
    assert p and [a["message"] for a in alerts] == ["Price shocks: up"]
    assert br.load_pulse_latest("uk", TODAY + timedelta(days=30), tmp_path / "pulse") is None  # stale
    plain = br.build_brief(uk_report(), br.load_needs(), today=TODAY)
    live = br.build_brief(uk_report(), br.load_needs(), p, alerts, today=TODAY)
    md = br.render_markdown(live)
    assert "The daily pulse reads 30" in md and "Alert, 28 November 2026" in md
    mm = lambda b: {n["id"]: n["evidence"] for n in b["needs"] + b["also"]}.get("money_control", 0)
    assert mm(live) > mm(plain)


# ---------------------------------------------------------------- calls

def test_calls_are_logged_once_per_need():
    b = br.build_brief(uk_report(), br.load_needs(), today=TODAY)
    calls = br.make_calls(b)
    assert len(calls) == br.TOP_NEEDS
    assert all(c.basis.startswith("need:") and c.check["geo"] == "GB" for c in calls)
    assert all(n["call"]["status"] == "logged" for n in b["needs"])
    again = br.build_brief(uk_report(), br.load_needs(), today=TODAY + timedelta(days=7), calls=calls)
    assert br.make_calls(again) == []
    assert all(n["call"]["status"] == "open" for n in again["needs"] if n["id"] in {c.basis[5:] for c in calls})


def weekly(start: date, end: date, value_for):
    out, d = [], start
    while d <= end:
        out.append((d.isoformat(), value_for(d)))
        d += timedelta(days=7)
    return out


def test_resolving_calls_compares_with_the_same_weeks_a_year_earlier():
    due = date(2027, 3, 1)
    mk = lambda i: Forecast(id=f"c{i}", question="q", probability=0.6, made_on="2026-11-30",
                            resolves_by=due.isoformat(), region="uk", basis="need:x",
                            check={"kind": "trends", "geo": "GB", "keywords": ["a"], "window_days": 28})
    up, down, early = mk(1), mk(2), mk(3)
    early.resolves_by = "2027-06-01"
    rising = lambda kw, geo, s, e: weekly(s, e, lambda d: 80.0 if d > due - timedelta(days=60) else 40.0)
    falling = lambda kw, geo, s, e: weekly(s, e, lambda d: 20.0 if d > due - timedelta(days=60) else 40.0)
    assert br.resolve_calls([up, early], date(2027, 3, 2), rising)[0]["outcome"] is True
    assert early.outcome is None  # not due yet, never fetched
    br.resolve_calls([down], date(2027, 3, 2), falling)
    assert down.outcome is False


def test_a_failed_trends_check_leaves_the_call_open():
    f = Forecast(id="c", question="q", probability=0.6, made_on="2026-11-30", resolves_by="2027-03-01",
                 region="uk", basis="need:x", check={"kind": "trends", "keywords": ["a"]})

    def boom(*a):
        raise RuntimeError("rate limited")
    res = br.resolve_calls([f], date(2027, 3, 8), boom)
    assert f.outcome is None and "could not check" in res[0]["result"]


def test_forecast_log_round_trip_keeps_old_rows_tidy(tmp_path):
    p = tmp_path / "f.json"
    old = Forecast(id="a", question="q", probability=0.4, made_on="2026-11-26", resolves_by="2027-05-31", region="uk")
    new = Forecast(id="b", question="q", probability=0.6, made_on="2026-11-30", resolves_by="2027-03-01",
                   region="uk", basis="need:x", check={"kind": "trends", "keywords": ["a"]})
    save_log(p, [old, new])
    rows = json.loads(p.read_text())
    assert "check" not in rows[0] and rows[1]["check"]["kind"] == "trends"
    assert load_log(p)[1].check == new.check
    assert load_log(ROOT / "data" / "forecasts.json")  # the existing log still loads


# ---------------------------------------------------------------- command line

def test_brief_command_writes_files_and_logs_calls(tmp_path, monkeypatch, capsys):
    import zeitgauge.cli as cli
    monkeypatch.setattr(br, "BRIEF_DATA_DIR", tmp_path / "brief")
    monkeypatch.setattr(br, "PULSE_DATA_DIR", tmp_path / "pulse")
    monkeypatch.setattr(br, "ALERT_DATA_DIR", tmp_path / "alerts")
    monkeypatch.setattr(cli, "WEB_BRIEF", tmp_path / "web" / "brief.json")
    log = tmp_path / "forecasts.json"
    # start from the hand-written calls only, so the real log's open need calls do not interfere
    save_log(log, [f for f in load_log(ROOT / "data" / "forecasts.json") if not f.basis.startswith("need:")])
    before = len(load_log(log))
    args = ["brief", "--region", "uk", "--web", "--log-calls", "--log", str(log), "--date", "2026-11-30"]
    assert main(args) == 0
    out = capsys.readouterr().out
    assert "What people need right now" in out and "Logged call at" in out
    assert len(load_log(log)) == before + br.TOP_NEEDS
    assert (tmp_path / "brief" / "uk" / "2026-11-30.md").exists()
    web = json.loads((tmp_path / "web" / "brief.json").read_text())
    assert web["regions"]["uk"]["needs"]
    args[-1] = "2026-12-07"
    assert main(args) == 0
    assert len(load_log(log)) == before + br.TOP_NEEDS  # a week later: same needs, no new calls
    assert "already a call since 30 November 2026" in capsys.readouterr().out


def test_brief_dry_run_writes_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(br, "BRIEF_DATA_DIR", tmp_path / "brief")
    log = tmp_path / "forecasts.json"
    assert main(["brief", "--region", "uk", "--dry-run", "--log-calls", "--log", str(log)]) == 0
    assert not log.exists() and not (tmp_path / "brief").exists()
    assert "Proposed call at" in capsys.readouterr().out


def test_brief_without_monthly_readings_says_so(capsys):
    assert main(["brief", "--region", "us", "--dry-run"]) == 1
    assert "No monthly readings" in capsys.readouterr().err

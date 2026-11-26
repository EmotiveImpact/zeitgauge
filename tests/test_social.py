from datetime import date, datetime, timezone

import pytest

from zeitgauge import social
from zeitgauge.social import Budget, OverBudget, charge, collect, daily_totals, history_file, pulse_signals, status
from zeitgauge.social import bluesky, reddit, x, youtube

DAY = date(2026, 11, 25)


class FakeHttp:
    """Returns canned replies in order and records every call."""

    def __init__(self, gets=(), posts=()):
        self.gets, self.posts, self.calls = list(gets), list(posts), []

    def get_json(self, url, headers=None):
        self.calls.append(("GET", url, headers))
        return self.gets.pop(0)

    def post_json(self, url, payload=None, headers=None, form=None):
        self.calls.append(("POST", url, payload or form))
        return self.posts.pop(0)


def cfg_with(**on):
    cfg = social.load_social()
    for platform, extra in on.items():
        cfg[platform] = {**cfg[platform], "enabled": True, **extra}
    return cfg


def test_everything_is_off_by_default():
    sts = status(social.load_social(), env={})
    assert {s.platform for s in sts} == {"bluesky", "youtube", "x", "reddit", "tiktok"}
    assert not any(s.ready for s in sts)
    assert next(s for s in sts if s.platform == "tiktok").blocker == "No official route for this use"


def test_switching_on_needs_secrets():
    cfg = cfg_with(x={})
    st = next(s for s in status(cfg, env={}) if s.platform == "x")
    assert not st.ready and st.blocker == "Missing secrets: X_BEARER_TOKEN"
    st = next(s for s in status(cfg, env={"X_BEARER_TOKEN": "t"}) if s.platform == "x")
    assert st.ready


def test_reddit_needs_written_approval_and_tiktok_never_runs():
    env = {"REDDIT_CLIENT_ID": "a", "REDDIT_CLIENT_SECRET": "b"}
    assert "approval" in next(s for s in status(cfg_with(reddit={}), env) if s.platform == "reddit").blocker
    assert next(s for s in status(cfg_with(reddit={"approved_use": True}), env) if s.platform == "reddit").ready
    assert not next(s for s in status(cfg_with(tiktok={}), {}) if s.platform == "tiktok").ready


def test_budget_stops_x_at_the_limit(tmp_path):
    cfg = cfg_with(x={"monthly_budget_usd": 0.01, "cost_per_request_usd": 0.005})
    b = Budget(tmp_path / "spend.json")
    now = datetime(2026, 11, 26, tzinfo=timezone.utc)
    charge(cfg, "x", 1, b)
    charge(cfg, "x", 1, b)
    with pytest.raises(OverBudget):
        charge(cfg, "x", 1, b)
    b.save()
    assert Budget(tmp_path / "spend.json").spent("x", now) == pytest.approx(0.01)


def test_x_counts_accepts_both_field_names():
    reply = {"data": [
        {"start": "2026-11-24T00:00:00.000Z", "end": "2026-11-25T00:00:00.000Z", "tweet_count": 120},
        {"start": "2026-11-25T00:00:00.000Z", "end": "2026-11-26T00:00:00.000Z", "post_count": 150},
        {"start": "2026-11-26T00:00:00.000Z", "end": "2026-11-26T10:00:00.000Z", "tweet_count": 40},
    ]}
    http = FakeHttp(gets=[reply])
    rows = x.count_rows({}, {"query": "skint lang:en"}, DAY, {"X_BEARER_TOKEN": "t"}, http)
    assert rows == [("2026-11-24", "all", 120, False), ("2026-11-25", "all", 150, False)]
    method, url, headers = http.calls[0]
    assert "granularity=day" in url and headers["Authorization"] == "Bearer t"


def test_x_hourly_drops_the_open_hour():
    reply = {"data": [{"start": f"2026-11-26T0{h}:00:00.000Z", "end": "", "tweet_count": h} for h in range(4)]}
    s = x.hourly_series("q", {"X_BEARER_TOKEN": "t"}, FakeHttp(gets=[reply]))
    assert s == [("2026-11-26T00:00", 0.0), ("2026-11-26T01:00", 1.0), ("2026-11-26T02:00", 2.0)]


def test_bluesky_signs_in_pages_and_marks_capped():
    full = {"posts": [{}] * 100, "cursor": "next"}
    http = FakeHttp(posts=[{"accessJwt": "jwt"}], gets=[full, full, {"posts": [{}] * 30}])
    rows = bluesky.count_rows({"max_pages": 2, "lang": "en"}, {"terms": ["skint", "food bank"]}, DAY,
                              {"BLUESKY_HANDLE": "me.bsky.social", "BLUESKY_APP_PASSWORD": "app-pw"}, http)
    assert rows == [("2026-11-25", "skint", 200, True), ("2026-11-25", "food bank", 30, False)]
    _, url, headers = http.calls[1]
    assert "since=2026-11-25T00%3A00%3A00Z" in url and "until=2026-11-26T00%3A00%3A00Z" in url
    assert headers["Authorization"] == "Bearer jwt"


def test_youtube_counts_new_videos():
    http = FakeHttp(gets=[{"items": [{}] * 12}, {"items": [{}] * 50, "nextPageToken": "p2"}])
    rows = youtube.count_rows({"max_pages": 1}, {"region_code": "GB", "terms": ["budget meals", "side hustle"]},
                              DAY, {"YOUTUBE_API_KEY": "k"}, http)
    assert rows == [("2026-11-25", "budget meals", 12, False), ("2026-11-25", "side hustle", 50, True)]
    assert youtube.quota_units({"max_pages": 1}, {"terms": ["a", "b"]}) == 200


def test_reddit_counts_only_that_day():
    in_day = datetime(2026, 11, 25, 12, tzinfo=timezone.utc).timestamp()
    out_day = datetime(2026, 11, 24, 12, tzinfo=timezone.utc).timestamp()
    listing = {"data": {"children": [{"data": {"created_utc": in_day}}, {"data": {"created_utc": out_day}}]}}
    http = FakeHttp(posts=[{"access_token": "tok"}], gets=[listing])
    rows = reddit.count_rows({}, {"subreddits": ["UKPersonalFinance"], "terms": ["skint"]}, DAY,
                             {"REDDIT_CLIENT_ID": "a", "REDDIT_CLIENT_SECRET": "b"}, http)
    assert rows == [("2026-11-25", "skint", 1, False)]


def test_collect_stores_counts_and_feeds_the_pulse(tmp_path):
    cfg = cfg_with(x={"cost_per_request_usd": 0.005, "monthly_budget_usd": 5})
    reply = {"data": [{"start": "2026-11-25T00:00:00.000Z", "end": "", "tweet_count": 150}]}
    report = collect(cfg, "uk", DAY, env={"X_BEARER_TOKEN": "t"}, http=FakeHttp(gets=[reply]),
                     budget=Budget(tmp_path / "spend.json"), data_dir=tmp_path)
    assert report == {"x": "1 rows, 150 posts on 2026-11-25"}
    assert daily_totals(history_file("uk", "x", tmp_path)) == [("2026-11-25", 150.0)]
    sigs = pulse_signals(cfg, "uk", data_dir=tmp_path)
    assert [s.id for s, _ in sigs] == ["social_x"] and sigs[0][0].direction == -1


def test_collect_reports_failures_without_stopping(tmp_path):
    cfg = cfg_with(x={}, youtube={})

    class Broken(FakeHttp):
        def get_json(self, url, headers=None):
            raise OSError("HTTP Error 403: Forbidden")

    report = collect(cfg, "uk", DAY, env={"X_BEARER_TOKEN": "t", "YOUTUBE_API_KEY": "k"}, http=Broken(),
                     budget=Budget(tmp_path / "s.json"), data_dir=tmp_path)
    assert report["x"].startswith("failed") and report["youtube"].startswith("failed")


def test_x_alert_watch_only_when_switched_on():
    assert social.x_alert_watch(cfg_with(x={}), "uk", env={"X_BEARER_TOKEN": "t"}) is None
    w = social.x_alert_watch(cfg_with(x={"hourly_alerts": True}), "uk", env={"X_BEARER_TOKEN": "t"})
    assert w["fetch"]["kind"] == "x_counts" and "lang:en" in w["fetch"]["query"]

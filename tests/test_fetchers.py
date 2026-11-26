from pathlib import Path

from zeitgauge.fetchers import latest_two, year_on_year
from zeitgauge.fetchers.boe import parse_boe
from zeitgauge.fetchers.fred import parse_fred
from zeitgauge.fetchers.ons import parse_ons
from zeitgauge.fetchers.trends import lead_lag_months

FX = Path(__file__).parent / "fixtures"


def test_parse_ons_prefers_months_and_skips_blanks():
    s = parse_ons((FX / "ons_d7g7.json").read_text())
    assert s[-1] == ("2026 OCT", 3.6)
    assert latest_two(s) == (3.6, 3.5, "2026 OCT")


def test_parse_fred_skips_dots():
    s = parse_fred((FX / "fred_unrate.csv").read_text())
    assert [v for _, v in s] == [4.3, 4.4, 4.5]


def test_parse_boe_dates_to_iso():
    s = parse_boe((FX / "boe_bankrate.csv").read_text())
    assert s[-1] == ("2026-10-31", 4.0)


def test_year_on_year():
    s = [(str(i), 100.0) for i in range(12)] + [("12", 103.0)]
    assert year_on_year(s) == [("12", 3.0)]


def test_lead_lag_finds_us_lead():
    us = [0, 0, 1, 3, 6, 3, 1, 0, 0, 0, 0, 0, 0]
    uk = [0, 0, 0, 0, 0, 1, 3, 6, 3, 1, 0, 0, 0]
    assert lead_lag_months(us, uk, max_lag=5) == 3

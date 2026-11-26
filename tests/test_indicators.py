import pytest

from zeitgauge.indicators.psi import PSIInputs, psi, to_signal
from zeitgauge.indicators.sahm import sahm_latest, sahm_series, triggered


def test_sahm_flat_unemployment_is_zero():
    assert set(sahm_series([4.0] * 20)) == {0.0}


def test_sahm_rise_triggers():
    rates = [4.0] * 14 + [4.3, 4.6, 4.9]
    latest, previous = sahm_latest(rates)
    assert latest == pytest.approx(0.6, abs=1e-3)
    assert triggered(latest)
    assert previous < latest


def test_sahm_needs_enough_history():
    with pytest.raises(ValueError):
        sahm_latest([4.0] * 10)


def test_psi_normal_year_is_one():
    r = psi(PSIInputs(1, 1, 1, 1, 1, 1))
    assert r["psi"] == 1.0 and r["reading"] == "normal"
    assert to_signal(1.0) == 0.0


def test_psi_pressures_multiply():
    r = psi(PSIInputs(rel_wage=0.9, youth_share=1.05, urban_share=1.0,
                      elite_ratio=1.2, debt_ratio=1.3, distrust=1.25))
    assert r["psi"] > 1.5 and r["reading"] == "elevated"
    assert to_signal(2.0) == -1.0


def test_psi_rejects_non_positive():
    with pytest.raises(ValueError):
        PSIInputs(0, 1, 1, 1, 1, 1)

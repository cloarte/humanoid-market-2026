"""FX conversion rules and label formatting."""

from __future__ import annotations

from datetime import date

import pytest

from src import fx, style

RATES = {"CNY": {date(2026, 3, 2): 7.0, date(2025, 12, 31): 7.1}}


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("2026-03-02", date(2026, 3, 2)),
        ("2025-12", date(2025, 12, 31)),
        ("2024-02", date(2024, 2, 29)),
        ("2025", date(2025, 12, 31)),
    ],
)
def test_event_date(given, expected):
    assert fx.event_date(given) == expected


def test_spot_uses_latest_earlier_observation():
    rate, obs = fx.spot("CNY", "2026-03-04", RATES)  # no observation on the 3rd or 4th
    assert (rate, obs) == (7.0, date(2026, 3, 2))


def test_spot_refuses_long_gaps():
    with pytest.raises(KeyError):
        fx.spot("CNY", "2026-04-30", RATES)


def test_to_usd():
    assert fx.to_usd(710, "CNY", "2025-12", RATES) == (100.0, 7.1, date(2025, 12, 31))
    assert fx.to_usd(5, "USD", "2025-12-01", RATES)[0] == 5


@pytest.mark.parametrize(
    ("value", "qualifier", "expected"),
    [
        (39e9, "", "$39B"),
        (5.5e9, "gt", ">$5.5B"),
        (520e6, "approx", "~$520M"),
        (13_500, "", "$13.5k"),
        (5_900, "", "$5,900"),
    ],
)
def test_fmt_usd(value, qualifier, expected):
    assert style.fmt_usd(value, qualifier) == expected


@pytest.mark.parametrize(
    ("value", "qualifier", "expected"),
    [
        (5168, "", "5,168 units"),
        (5500, "gt", ">5,500 units"),
        (100, "lt", "<100 units"),
        (1.4e6, "approx", "~1.4M units"),
    ],
)
def test_fmt_units(value, qualifier, expected):
    assert style.fmt_units(value, qualifier) == expected


def test_takeaway_word_limit():
    assert style.check_takeaway("Fifteen words or fewer is fine.")
    with pytest.raises(ValueError):
        style.check_takeaway(" ".join(["word"] * 16))

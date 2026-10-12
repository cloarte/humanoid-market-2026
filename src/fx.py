"""Currency conversion with documented reference rates.

Rate source
-----------
Federal Reserve Board, H.10 "Foreign Exchange Rates" (noon buying rates in New York,
certified by the Federal Reserve Bank of New York), retrieved through FRED, Federal
Reserve Bank of St. Louis. One series per currency, listed in FRED_SERIES below.

Convention
----------
`rate` = units of local currency per 1 USD, so `usd = local / rate`.
Series quoted as USD per unit (EUR, GBP) are inverted when fetched.

Which date
----------
Amounts are converted at the rate on the event date: the announcement date for a
round, the deal/listing/market-cap date for a valuation, and the last day of the
reporting period for revenue and net income. H.10 publishes no rate on weekends or
US holidays; we then use the most recent earlier observation (never an interpolated
value) and record its date in `fx_date`. When the source dates the event only to a
month or a year (e.g. `2025-12`), we use the last observation in that period.

All observations used are committed in data/fx_rates.csv so every conversion can be
re-checked offline. Refresh with:

    python -m src.fx --fetch CNY HKD --start 2024-01-01
    python -m src.fx --convert 2500000000 CNY 2026-03-02
"""

from __future__ import annotations

import argparse
import calendar
import csv
import io
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RATES_CSV = ROOT / "data" / "fx_rates.csv"
SOURCE_NAME = "Federal Reserve Board H.10 via FRED (St. Louis Fed)"
MAX_GAP_DAYS = 7  # refuse to reach further back than this for a missing day

# currency -> (FRED series id, True if the series is quoted as USD per unit of currency)
FRED_SERIES = {
    "CNY": ("DEXCHUS", False),
    "HKD": ("DEXHKUS", False),
    "EUR": ("DEXUSEU", True),
    "GBP": ("DEXUSUK", True),
}
FIELDS = ["date", "currency", "rate", "series_id", "source_url", "source_name"]


def series_url(series_id: str) -> str:
    return f"https://fred.stlouisfed.org/series/{series_id}"


def event_date(d: str | date) -> date:
    """Date to convert at: the date itself, or the last day of a month (`2025-12`) or year (`2025`)."""
    if isinstance(d, date):
        return d
    parts = [int(p) for p in d.split("-")]
    if len(parts) == 3:
        return date(*parts)
    if len(parts) == 2:
        return date(parts[0], parts[1], calendar.monthrange(parts[0], parts[1])[1])
    return date(parts[0], 12, 31)


def load_rates() -> dict[str, dict[date, float]]:
    rates: dict[str, dict[date, float]] = {}
    if not RATES_CSV.exists():
        return rates
    with RATES_CSV.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rates.setdefault(r["currency"], {})[date.fromisoformat(r["date"])] = float(r["rate"])
    return rates


def spot(currency: str, on: str | date, rates: dict | None = None) -> tuple[float, date]:
    """Rate on `on`, or the latest earlier observation within MAX_GAP_DAYS. Returns (rate, obs_date)."""
    rates = load_rates() if rates is None else rates
    series = rates.get(currency)
    if not series:
        raise KeyError(f"no {currency} rates in {RATES_CSV.name}; run: python -m src.fx --fetch {currency}")
    day = event_date(on)
    for back in range(MAX_GAP_DAYS + 1):
        d = day - timedelta(days=back)
        if d in series:
            return series[d], d
    raise KeyError(f"no {currency} observation within {MAX_GAP_DAYS} days before {day}")


def to_usd(amount: float, currency: str, on: str | date, rates: dict | None = None) -> tuple[float, float, date]:
    """Convert at the event-date rate. Returns (usd, rate, obs_date)."""
    if currency == "USD":
        return amount, 1.0, event_date(on)
    rate, obs = spot(currency, on, rates)
    return amount / rate, rate, obs


def fetch(currencies: list[str], start: str, end: str | None = None) -> int:
    """Download H.10 series from FRED and merge into data/fx_rates.csv. Returns rows written."""
    end = end or date.today().isoformat()
    existing: dict[tuple[str, str], dict] = {}
    if RATES_CSV.exists():
        with RATES_CSV.open(encoding="utf-8", newline="") as f:
            existing = {(r["date"], r["currency"]): r for r in csv.DictReader(f)}
    for ccy in currencies:
        series_id, inverted = FRED_SERIES[ccy]
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}&coed={end}"
        # Keep urllib's default User-Agent: FRED stalls on some custom ones.
        with urllib.request.urlopen(url, timeout=60) as resp:
            text = resp.read().decode("utf-8")
        rows = list(csv.reader(io.StringIO(text)))
        for d, v in rows[1:]:
            if v in ("", "."):
                continue  # no observation that day (holiday)
            rate = 1 / float(v) if inverted else float(v)
            existing[(d, ccy)] = {
                "date": d,
                "currency": ccy,
                "rate": f"{rate:.6f}".rstrip("0").rstrip("."),
                "series_id": series_id,
                "source_url": series_url(series_id),
                "source_name": SOURCE_NAME,
            }
    out = sorted(existing.values(), key=lambda r: (r["currency"], r["date"]))
    with RATES_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    return len(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", nargs="+", metavar="CCY", help="currencies to download from FRED")
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--convert", nargs=3, metavar=("AMOUNT", "CCY", "DATE"), help="convert one amount to USD")
    a = ap.parse_args()
    if a.fetch:
        n = fetch([c.upper() for c in a.fetch], a.start, a.end)
        print(f"{RATES_CSV.relative_to(ROOT)}: {n} rows")
    if a.convert:
        amount, ccy, on = float(a.convert[0]), a.convert[1].upper(), a.convert[2]
        usd, rate, obs = to_usd(amount, ccy, on)
        print(f"{amount:,.0f} {ccy} / {rate} (H.10, {obs}) = {usd:,.0f} USD")
    if not (a.fetch or a.convert):
        ap.print_help(sys.stderr)


if __name__ == "__main__":
    main()

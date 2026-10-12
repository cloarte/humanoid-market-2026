"""Shared data access and selection rules for the charts.

Every chart reads the CSVs in data/ through this module, so the rules that pick one number
out of several sources live in one place and can be reviewed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src import fx

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# Market caps are compared on one date; private valuations are the latest round at or before the cut-off.
MARKET_CAP_DATE = "2026-09-30"
CUTOFF = "2026-10-12"


def load(table: str) -> pd.DataFrame:
    """A table as strings (empty cells are ''), exactly as stored."""
    return pd.read_csv(DATA / f"{table}.csv", dtype=str, keep_default_na=False)


def num(value: str) -> float | None:
    return float(value) if value not in ("", None) else None


@dataclass(frozen=True)
class Valuation:
    company_id: str
    value_usd: float
    qualifier: str  # eq / approx / gt ...
    basis: str  # "market cap", "post-money", "pre-money", "valuation" (basis not stated)
    date: str
    status: str  # closed / announced / in_talks / term_sheet / listed
    source_name: str
    source_url: str
    confidence: str  # V / R / U of the source that gives the value


BASIS_PREFERENCE = (("post_money_usd", "post-money"), ("valuation_usd", "valuation"), ("pre_money_usd", "pre-money"))
CONFIDENCE_RANK = {"V": 0, "R": 1, "U": 2}


def _round_valuations(rounds: pd.DataFrame) -> list[Valuation]:
    """One valuation per deal: the explicit post-money if any source gives it, else the best other source."""
    out = []
    for _, deal in rounds.groupby("round_id"):
        candidates = []
        for _, r in deal.iterrows():
            for col, basis in BASIS_PREFERENCE:
                if r[col]:
                    rank = (BASIS_PREFERENCE.index((col, basis)), CONFIDENCE_RANK[r["confidence"]])
                    candidates.append((rank, r, col, basis))
                    break
        if not candidates:
            continue
        _, r, col, basis = min(candidates, key=lambda c: c[0])
        out.append(
            Valuation(
                r["company_id"],
                float(r[col]),
                r["valuation_qualifier"] or "eq",
                basis,
                r["date"],
                r["status"],
                r["source_name"],
                r["source_url"],
                r["confidence"],
            )
        )
    return out


def valuations(include_pending: bool = False) -> dict[str, Valuation]:
    """Latest valuation per company, by this rule:

    1. Listed companies: market capitalisation on MARKET_CAP_DATE (valuations_revenue).
    2. Private companies: the most recent round that is `closed` or `announced`
       (funding_rounds), preferring an explicit post-money figure, then a figure whose basis
       is not stated, then pre-money; among sources, the most reliable confidence grade.
    3. With `include_pending=True`, returns instead the most recent `in_talks` / `term_sheet`
       valuation that is newer than the company's rule-1/2 valuation (drawn as dashed marks).
    """
    rounds = load("funding_rounds")
    caps = load("valuations_revenue")
    caps = caps[(caps["valuation_type"] == "market_cap") & (caps["date"] == MARKET_CAP_DATE)]
    listed = {
        r["company_id"]: Valuation(
            r["company_id"],
            float(r["valuation_usd"]),
            r["valuation_qualifier"] or "eq",
            "market cap",
            r["date"],
            "listed",
            r["source_name"],
            r["source_url"],
            r["confidence"],
        )
        for _, r in caps.iterrows()
    }

    done = [v for v in _round_valuations(rounds[rounds["status"].isin(["closed", "announced"])])]
    pending = [v for v in _round_valuations(rounds[rounds["status"].isin(["in_talks", "term_sheet"])])]

    def latest(items: list[Valuation]) -> dict[str, Valuation]:
        best: dict[str, Valuation] = {}
        for v in sorted(items, key=lambda v: fx.event_date(v.date)):
            best[v.company_id] = v
        return best

    settled = latest(done) | listed  # a market cap overrides private rounds
    if not include_pending:
        return settled
    newer = {}
    for cid, v in latest(pending).items():
        base = settled.get(cid)
        if base is None or fx.event_date(v.date) > fx.event_date(base.date):
            newer[cid] = v
    return newer


BOUNDS = ("gt", "gte", "lt", "lte", "approx", "range")


def annual_revenue(year: str) -> pd.DataFrame:
    """One revenue row per company for a full year (index kept, for row references). When several sources
    give the year: an exact figure before a bound, then the more reliable source, then the newest."""
    vr = load("valuations_revenue")
    vr = vr[(vr["revenue_usd"] != "") & vr["revenue_scope"].isin(["total", "unspecified"])]
    vr = vr[vr["revenue_period"].str.fullmatch(rf"(FY)?{year}")]
    order = vr.assign(
        _bound=vr["revenue_qualifier"].isin(BOUNDS), _conf=vr["confidence"].map(CONFIDENCE_RANK)
    ).sort_values(["company_id", "_bound", "_conf", "source_date"], ascending=[True, True, True, False])
    return order.drop_duplicates("company_id").drop(columns=["_bound", "_conf"])


def omdia_units_2025() -> dict[str, tuple[float, str]]:
    """Omdia's 2025 shipment estimates: company_id -> (units, qualifier)."""
    s = load("shipments")
    s = s[(s["data_provider"] == "Omdia") & (s["year"] == "2025") & (s["metric"] == "shipped")]
    return {r["company_id"]: (float(r["units"]), r["units_qualifier"] or "eq") for _, r in s.iterrows()}


def company_units_2025() -> dict[str, tuple[float, str]]:
    """Units the companies themselves report for 2025 (shipped)."""
    s = load("shipments")
    s = s[(s["source_type"] == "company") & (s["year"] == "2025") & (s["period"] == "FY") & (s["metric"] == "shipped")]
    return {r["company_id"]: (float(r["units"]), r["units_qualifier"] or "eq") for _, r in s.iterrows() if r["units"]}


def companies() -> pd.DataFrame:
    return load("companies").set_index("company_id")

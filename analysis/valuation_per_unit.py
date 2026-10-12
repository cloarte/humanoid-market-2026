"""Valuation per robot shipped in 2025: an order of magnitude, not a multiple.

Run:  python -m analysis.valuation_per_unit      -> prints the table, writes outputs/valuation_per_unit.csv

Scope: humanoid makers with both an Omdia 2025 shipment row and a closed or announced valuation
(robot AI labs ship no robots; Tesla's Optimus has no valuation of its own). Units are Omdia's,
because Omdia applies one definition to every maker; company-reported counts, where they exist,
give the sensitivity columns.
"""

from __future__ import annotations

import pandas as pd

from charts import data
from src import style

OUT = style.OUTPUTS / "valuation_per_unit.csv"
LOWER_BOUND = ("gt", "gte")
GENERAL_CAVEAT = (
    "Order of magnitude, not a multiple: a point-in-time valuation divided by one year of shipments; "
    "valuation bases and dates differ between companies."
)


def valuation_basis(v: data.Valuation, status: str) -> str:
    if v.basis == "market cap":
        return "stock market value"
    return "SPAC merger value" if status == "spac_pending" else "funding round"


def row_ref(table: str, df: pd.DataFrame, mask: pd.Series) -> str:
    hit = df[mask]
    if len(hit) != 1:
        raise LookupError(f"{table}: {len(hit)} rows")
    return f"{table}.csv:{hit.index[0] + 2}"


# Judgement calls taken by the author (round 2 brief, 2026-10-12), kept apart from the data-driven caveats.
DECIDED_CAVEATS = {"agibot": "Its last valuation likely understates its current value."}


def month(date: str) -> str:
    return pd.Timestamp(date[:7] + "-01").strftime("%b %Y") if len(date) >= 7 else date


def specific_caveat(
    cid: str, v: data.Valuation, units_qualifier: str, own: tuple[float, str] | None, same_estimate: list[str]
) -> str:
    """What a reader must know about this one row, built from the data."""
    notes = []
    cutoff = pd.Timestamp(data.CUTOFF)
    if v.basis != "market cap" and pd.Timestamp(data.fx.event_date(v.date)) < cutoff - pd.DateOffset(years=1):
        notes.append(f"Valuation dates from {month(v.date)}, more than a year before the data cut-off.")
    if cid in DECIDED_CAVEATS:
        notes.append(DECIDED_CAVEATS[cid])
    if v.qualifier == "approx":
        notes.append("Valuation is approximate.")
    if not own:
        notes.append("Units are Omdia's estimate; the company discloses no count.")
        if len(same_estimate) > 1:
            names = ", ".join(same_estimate[:-1]) + " and " + same_estimate[-1]
            notes.append(f"Omdia gives the same figure to {names}.")
    else:
        sym = style.QUALIFIER_SYMBOL[own[1]]
        notes.append(f"The company reports {sym}{own[0]:,.0f} units (see the sensitivity columns).")
    if units_qualifier:
        notes.append(f"Omdia's figure is stated as '{style.QUALIFIER_SYMBOL[units_qualifier]}'.")
    return " ".join(notes)


def table() -> pd.DataFrame:
    co = data.companies()
    vals = data.valuations()
    shipments = data.load("shipments")
    omdia = data.omdia_units_2025()
    own = data.company_units_2025()
    rows = []
    for cid, (units, units_q) in omdia.items():
        if cid not in vals or co.loc[cid, "segment"] != "humanoid_fullstack":
            continue
        v = vals[cid]
        per_unit = v.value_usd / units
        company = own.get(cid)
        units_ref = row_ref(
            "shipments",
            shipments,
            (shipments["company_id"] == cid) & (shipments["year"] == "2025") & (shipments["data_provider"] == "Omdia"),
        )
        refs = [units_ref, _valuation_ref(v)]
        sensitivity, sensitivity_note = None, ""
        if company:
            sensitivity = v.value_usd / company[0]
            refs.append(
                row_ref(
                    "shipments",
                    shipments,
                    (shipments["company_id"] == cid)
                    & (shipments["year"] == "2025")
                    & (shipments["source_type"] == "company")
                    & (shipments["metric"] == "shipped"),
                )
            )
            # More units than stated means a lower value per unit: the result is an upper bound.
            sensitivity_note = "at most" if company[1] in LOWER_BOUND else "exact"
        same = [co.loc[c, "name"] for c, (u, _) in omdia.items() if u == units and c in co.index]
        caveat = specific_caveat(cid, v, units_q if units_q != "eq" else "", company, same)
        rows.append(
            {
                "company_id": cid,
                "country": co.loc[cid, "country"],
                "units_2025_omdia": int(units),
                "valuation_usd": round(v.value_usd),
                "valuation_qualifier": v.qualifier if v.qualifier != "eq" else "",
                "valuation_basis": valuation_basis(v, co.loc[cid, "status"]),
                "valuation_date": v.date,
                "valuation_per_unit_usd": round(per_unit),
                "units_source_type": "third-party estimate (Omdia)",
                "units_company_reported": int(company[0]) if company else "",
                "units_company_qualifier": company[1] if company and company[1] != "eq" else "",
                "valuation_per_unit_company_units_usd": round(sensitivity) if sensitivity else "",
                "company_units_bound": sensitivity_note,
                "caveat": f"{GENERAL_CAVEAT} {caveat}",
                "rows_used": "; ".join(refs),
            }
        )
    return pd.DataFrame(rows).sort_values("valuation_per_unit_usd", ascending=False)


def _valuation_ref(v: data.Valuation) -> str:
    for name in ("valuations_revenue", "funding_rounds"):
        df = data.load(name)
        mask = (df["company_id"] == v.company_id) & (df["date"] == v.date) & (df["source_url"] == v.source_url)
        if mask.any():
            return f"{name}.csv:{df[mask].index[0] + 2}"
    raise LookupError(v)


def main() -> pd.DataFrame:
    out = table()
    style.OUTPUTS.mkdir(exist_ok=True)
    out.to_csv(OUT, index=False, lineterminator="\n")
    shown = out.assign(
        valuation=[style.fmt_usd(v, q) for v, q in zip(out["valuation_usd"], out["valuation_qualifier"], strict=True)],
        per_unit=out["valuation_per_unit_usd"].map(style.fmt_usd),
        per_unit_company=[
            f"{'≤' if b == 'at most' else ''}{style.fmt_usd(x)}" if x != "" else ""
            for x, b in zip(out["valuation_per_unit_company_units_usd"], out["company_units_bound"], strict=True)
        ],
    )
    cols = [
        "company_id",
        "units_2025_omdia",
        "valuation",
        "valuation_basis",
        "valuation_date",
        "per_unit",
        "per_unit_company",
        "rows_used",
    ]
    print(shown[cols].to_string(index=False))
    print(f"\n{OUT}")
    return out


if __name__ == "__main__":
    main()

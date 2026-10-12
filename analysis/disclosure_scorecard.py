"""Disclosure scorecard: what each humanoid maker publicly discloses about useful work.

Run:  python -m analysis.disclosure_scorecard
      -> outputs/disclosure_scorecard.csv (one row per company and item, with its evidence)
         outputs/dw_06_disclosure_scorecard.csv (one row per company, for the Datawrapper table)

An evidence audit, not a ranking of quality. Every cell is decided by the rules below from the rows in
data/; the definitions are in DATA_DICTIONARY.md. Third-party estimates (e.g. Omdia) never count as a
company disclosure. ✗ means "not found in the public sources reviewed as of the data cut-off"; what was
searched is logged in GAPS.md.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pandas as pd

from charts import data
from src import style

OUT = style.OUTPUTS / "disclosure_scorecard.csv"
OUT_DW = style.OUTPUTS / "dw_06_disclosure_scorecard.csv"
SCOPE = (
    "agibot",
    "unitree",
    "ubtech",
    "galbot",
    "x-square-robot",
    "figure-ai",
    "apptronik",
    "agility-robotics",
    "1x-technologies",
    "tesla",
)
YES, PARTIAL, NO = "✓", "◐", "✗"
FIRST_PARTY = ("regulatory_filing", "customer_statement", "company_statement")
LOWER_OR_ROUGH = ("gt", "gte", "lt", "lte", "approx", "range")
NOT_FOUND = "Not found in the public sources reviewed as of 12 Oct 2026 (see GAPS.md)."


@dataclass
class Cell:
    status: str
    rows: list[str] = field(default_factory=list)  # evidence rows, as file.csv:line
    source_url: str = ""
    note: str = ""


@dataclass
class Tables:
    shipments: pd.DataFrame
    revenue: pd.DataFrame
    evidence: pd.DataFrame
    items: pd.DataFrame
    companies: pd.DataFrame

    @classmethod
    def load(cls) -> Tables:
        rev = data.load("valuations_revenue")
        return cls(
            data.load("shipments"),
            rev[rev["revenue_usd"] != ""],
            data.load("deployment_evidence"),
            data.load("company_financial_items"),
            data.companies(),
        )


def ref(table: str, index: int) -> str:
    return f"{table}.csv:{index + 2}"


def cell_from(table: str, row_index: int, row: pd.Series, status: str, note: str) -> Cell:
    return Cell(status, [ref(table, row_index)], row["source_url"], note)


# --- One rule per column ---------------------------------------------------------------------


def units(t: Tables, cid: str) -> Cell:
    s = t.shipments[(t.shipments["company_id"] == cid) & (t.shipments["source_type"] == "company")]
    shipped = s[(s["metric"] == "shipped") & (s["units"] != "")]
    full_year = shipped[shipped["period"] == "FY"]
    if len(full_year):
        i = full_year.sort_values("year").index[-1]
        r = full_year.loc[i]
        q = r["units_qualifier"]
        status = PARTIAL if q in LOWER_OR_ROUGH else YES
        note = f"{style.QUALIFIER_SYMBOL.get(q or 'eq', '')}{float(r['units']):,.0f} in {r['year']}"
        return cell_from("shipments", i, r, status, note + (" (stated as a bound)" if status == PARTIAL else ""))
    if len(shipped):  # cumulative or part of a year only
        i = shipped.index[0]
        r = shipped.loc[i]
        sym = style.QUALIFIER_SYMBOL.get(r["units_qualifier"] or "eq", "")
        when = f" to {r['as_of']}" if r["as_of"] else f" in {r['period']} {r['year']}"
        return cell_from(
            "shipments", i, r, PARTIAL, f"{sym}{float(r['units']):,.0f} {r['period']}{when}; no full-year figure"
        )
    other = s[s["metric"] != "shipped"]
    if len(other):
        r = other.iloc[0]
        what = r["units_text"] or f"{style.QUALIFIER_SYMBOL.get(r['units_qualifier'] or 'eq', '')}{r['units']}"
        return Cell(
            NO,
            [ref("shipments", other.index[0])],
            r["source_url"],
            f"No shipments figure; the company states {r['metric']}: {what}.",
        )
    return Cell(NO, note=NOT_FOUND)


def revenue(t: Tables, cid: str) -> Cell:
    r = t.revenue[(t.revenue["company_id"] == cid) & t.revenue["revenue_scope"].isin(["total", "unspecified"])]
    full_years = r[r["revenue_period"].str.fullmatch(r"(FY)?\d{4}")]
    if not len(full_years):
        st = t.items[(t.items["company_id"] == cid) & (t.items["item"] == "statutory_revenue")]
        if len(st):
            i = st.index[0]
            row = st.loc[i]
            note = (
                f"{float(row['value']):,.0f} {row['unit']} in {row['period']}, from the statutory accounts of a "
                "subsidiary only; group revenue not disclosed"
            )
            return cell_from("company_financial_items", i, row, PARTIAL, note)
        return Cell(NO, note=NOT_FOUND)
    # Latest year; within it, an exact figure before a bound, then the more reliable and newer source.
    order = full_years.assign(
        _bound=full_years["revenue_qualifier"].isin(LOWER_OR_ROUGH),
        _conf=full_years["confidence"].map(data.CONFIDENCE_RANK),
    ).sort_values(["revenue_period", "_bound", "_conf", "source_date"], ascending=[False, True, True, False])
    i = order.index[0]
    row = full_years.loc[i]
    q = row["revenue_qualifier"]
    status = PARTIAL if q in LOWER_OR_ROUGH or row["confidence"] != "V" else YES
    note = f"{style.fmt_usd(float(row['revenue_usd']), q)} in {row['revenue_period'].replace('FY', '')}"
    if status == PARTIAL:
        note += "; stated as a bound or self-reported"
    return cell_from("valuations_revenue", i, row, status, note)


def paid_deployment(t: Tables, cid: str) -> Cell:
    e = t.evidence[
        (t.evidence["company_id"] == cid) & t.evidence["metric"].isin(["robots_deployed", "robots_doing_useful_work"])
    ]
    paid = e[(e["stage"] == "commercial") & (e["value"] != "")]
    if len(paid):
        i = paid.index[0]
        r = paid.loc[i]
        status = YES if r["verification"] in FIRST_PARTY else PARTIAL
        sym = style.QUALIFIER_SYMBOL.get(r["value_qualifier"] or "eq", "")
        note = f"{sym}{float(r['value']):,.0f} {r['unit']} at {r['customer']} ({r['as_of']})"
        if status == PARTIAL:
            note += "; count reported by the press, not by the company"
        return cell_from("deployment_evidence", i, r, status, note)
    if len(e):
        i = e.index[0]
        r = e.loc[i]
        return cell_from(
            "deployment_evidence",
            i,
            r,
            NO,
            f"Only {r['stage']} use: {r['value'] or r['value_text']} {r['unit']} ({r['as_of']}).",
        )
    hours = t.evidence[(t.evidence["company_id"] == cid) & (t.evidence["metric"] == "operating_hours")]
    if len(hours):
        return Cell(
            NO,
            [ref("deployment_evidence", hours.index[0])],
            hours.iloc[0]["source_url"],
            "Hours are disclosed, but not how many robots are at work.",
        )
    return Cell(NO, note=NOT_FOUND)


def hours(t: Tables, cid: str) -> Cell:
    e = t.evidence[(t.evidence["company_id"] == cid) & (t.evidence["metric"] == "operating_hours")]
    if not len(e):
        return Cell(NO, note=NOT_FOUND)
    i = e.index[0]
    r = e.loc[i]
    first_hand = r["stage"] == "commercial" and r["verification"] in FIRST_PARTY and r["confidence"] == "V"
    note = (
        f"{style.QUALIFIER_SYMBOL.get(r['value_qualifier'] or 'eq', '')}{float(r['value']):,.0f} hours ({r['stage']})"
    )
    if r["stage"] != "commercial":
        note += "; a pilot, not paid use"
    elif not first_hand:
        note += "; secondary report"
    return cell_from("deployment_evidence", i, r, YES if first_hand else PARTIAL, note)


def customer(t: Tables, cid: str) -> Cell:
    e = t.evidence[(t.evidence["company_id"] == cid) & (t.evidence["customer"] != "")]
    e = e[~e["customer"].str.startswith("Undisclosed") & e["stage"].isin(["commercial", "pilot", "contracted"])]
    first_hand = e[e["verification"].isin(FIRST_PARTY)]
    if len(first_hand):
        i = first_hand.index[0]
        r = first_hand.loc[i]
        return cell_from("deployment_evidence", i, r, YES, f"{r['customer']} ({r['stage']})")
    sales = t.items[(t.items["company_id"] == cid) & (t.items["item"] == "net_sales_to_customer")]
    if len(sales):
        i = sales.index[0]
        r = sales.loc[i]
        return cell_from("company_financial_items", i, r, YES, f"{r['counterparty']}: sales in {r['period']} (filing)")
    if len(e):
        i = e.index[0]
        r = e.loc[i]
        note = f"{r['customer']} ({r['stage']}); reported by the press, not by the company or the customer"
        return cell_from("deployment_evidence", i, r, PARTIAL, note)
    return Cell(NO, note=NOT_FOUND)


# Unit of a financial item -> (revenue column it compares with, multiplier to that column's unit)
UNIT_SCALE = {
    "USD": ("revenue_usd", 1),
    "RMB thousand": ("revenue_local", 1e3),
    "RMB 10 thousand": ("revenue_local", 1e4),
}


def related_parties(t: Tables, cid: str) -> Cell:
    it = t.items[(t.items["company_id"] == cid) & (t.items["item"] == "net_sales_related_parties")]
    if not len(it):
        return Cell(NO, note=NOT_FOUND)
    i = it.index[0]
    r = it.loc[i]
    col, scale = UNIT_SCALE[r["unit"]]
    amount = float(r["value"]) * scale
    shown = style.fmt_usd(amount) if col == "revenue_usd" else f"RMB {amount / 1e6:,.1f}M"
    note = f"{shown} in {r['period']}"
    rows = [ref("company_financial_items", i)]
    total = data.annual_revenue(r["period"].replace("FY", ""))
    total = total[total["company_id"] == cid]
    if len(total):
        note += f", {amount / float(total.iloc[0][col]):.1%} of revenue"
        rows.append(ref("valuations_revenue", total.index[0]))
    return Cell(YES, rows, r["source_url"], note)


def audited(t: Tables, cid: str) -> Cell:
    c = t.companies.loc[cid]
    if c["status"] == "public" and c["segment"] == "big_tech_program":
        return Cell(
            PARTIAL,
            note=f"Group accounts are audited ({c['exchange']}: {c['ticker']}); the humanoid "
            "programme is not reported separately.",
        )
    if c["status"] == "public":
        return Cell(YES, note=f"Listed company ({c['exchange']}: {c['ticker']}).")
    audited_rows = t.revenue[(t.revenue["company_id"] == cid) & t.revenue["notes"].str.startswith("Audited")]
    if len(audited_rows):
        i = audited_rows.index[0]
        return cell_from("valuations_revenue", i, audited_rows.loc[i], YES, "Audited statements in an SEC filing.")
    subsidiary = t.items[(t.items["company_id"] == cid) & (t.items["item"] == "accounts_audited")]
    if len(subsidiary):
        i = subsidiary.index[0]
        note = "Only a subsidiary's statutory accounts are public and audited; no group accounts."
        return cell_from("company_financial_items", i, subsidiary.loc[i], PARTIAL, note)
    return Cell(NO, note="Private company; no audited statements found in public filings.")


# item -> (short header for the table, what a ✓ means in a sentence, rule)
COLUMNS: dict[str, tuple[str, str, Callable[[Tables, str], Cell]]] = {
    "units": ("Units", "state how many robots they shipped or sold", units),
    "revenue": ("Revenue", "state their revenue", revenue),
    "paid_deployment": ("At work", "say how many robots are in paid work", paid_deployment),
    "hours": ("Hours", "report operating hours at customers", hours),
    "customer": ("Customer", "name a paying customer", customer),
    "related_parties": ("Rel. party", "disclose sales to related parties", related_parties),
    "audited": ("Audited", "publish audited accounts", audited),
}


def scorecard() -> pd.DataFrame:
    """Long format: one row per company and item."""
    t = Tables.load()
    rows = []
    for cid in SCOPE:
        for key, (_, _, rule) in COLUMNS.items():
            c = rule(t, cid)
            rows.append(
                {
                    "company_id": cid,
                    "company": t.companies.loc[cid, "name"],
                    "country": t.companies.loc[cid, "country"],
                    "item": key,
                    "status": c.status,
                    "evidence_rows": "; ".join(c.rows),
                    "source_url": c.source_url,
                    "note": c.note,
                }
            )
    return pd.DataFrame(rows)


def summary(long: pd.DataFrame) -> dict[str, str]:
    """One line per item: 'X of N companies disclose …', computed from the table."""
    n = long["company_id"].nunique()
    out = {}
    for key, (_, sentence, _) in COLUMNS.items():
        col = long[long["item"] == key]
        yes, part = (col["status"] == YES).sum(), (col["status"] == PARTIAL).sum()
        out[key] = f"{yes} of {n} humanoid makers {sentence}" + (f" ({part} more in part)" if part else "") + "."
    return out


def wide(long: pd.DataFrame) -> pd.DataFrame:
    """Company plus one symbol column per item, for the Datawrapper table."""
    table = long.pivot(index="company", columns="item", values="status")[list(COLUMNS)]
    table.columns = [COLUMNS[k][0] for k in COLUMNS]
    order = [long[long["company_id"] == cid]["company"].iloc[0] for cid in SCOPE]
    table = table.loc[order].reset_index().rename(columns={"company": "Company"})
    country = long.drop_duplicates("company").set_index("company")["country"]
    table.insert(1, "Country", table["Company"].map(country).map({"CN": "China", "US": "US", "GB": "UK"}))
    return table


def main() -> pd.DataFrame:
    long = scorecard()
    style.OUTPUTS.mkdir(exist_ok=True)
    long.to_csv(OUT, index=False, lineterminator="\n")
    wide(long).to_csv(OUT_DW, index=False, lineterminator="\n")
    print(wide(long).to_string(index=False))
    print()
    for line in summary(long).values():
        print(line)
    print(f"\n{OUT}\n{OUT_DW}")
    return long


if __name__ == "__main__":
    main()

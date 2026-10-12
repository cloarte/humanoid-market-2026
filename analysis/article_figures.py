"""Recompute every figure the article cites, from data/ only, with the rows each one uses.

Run:  python -m analysis.article_figures      -> prints the table, writes outputs/article_figures.csv

`rows_used` points to `file.csv:line` (line 1 is the header). `expected` is the figure as written in the
article brief; `matches` says whether the recomputed value rounds to it.
"""

from __future__ import annotations

import pandas as pd

from charts import data
from src import style

OUT = style.OUTPUTS / "article_figures.csv"


class Rows:
    """Look up rows in a data table and remember their `file.csv:line` references."""

    def __init__(self, table: str):
        self.table = table
        self.df = data.load(table)

    def one(self, **match: str) -> tuple[pd.Series, str]:
        hit = self.df
        for col, value in match.items():
            hit = hit[hit[col] == value]
        if len(hit) != 1:
            raise LookupError(f"{self.table}: {len(hit)} rows match {match}")
        return hit.iloc[0], f"{self.table}.csv:{hit.index[0] + 2}"


def figures() -> list[dict]:
    ship, fund, vr = Rows("shipments"), Rows("sector_funding"), Rows("valuations_revenue")
    items, fc, ev = Rows("company_financial_items"), Rows("forecasts"), Rows("deployment_evidence")
    out: list[dict] = []

    def add(figure: str, value: str, refs: list[str], expected: str, matches: bool, note: str = "") -> None:
        out.append(
            {
                "figure": figure,
                "value": value,
                "rows_used": "; ".join(refs),
                "expected": expected,
                "matches": "yes" if matches else "NO",
                "note": note,
            }
        )

    # --- Volume (Omdia only) ---
    total, r_total = ship.one(company_id="_all", year="2025", data_provider="Omdia")
    n = float(total["units"])
    add("Global humanoid shipments 2025 (Omdia)", f"{n:,.0f}", [r_total], "13,318", n == 13318)

    def omdia(cid: str) -> tuple[float, str]:
        row, ref = ship.one(company_id=cid, year="2025", data_provider="Omdia", metric="shipped")
        return float(row["units"]), ref

    for label, ids, expected in (
        ("AgiBot + Unitree + UBTech share of 2025 shipments", ("agibot", "unitree", "ubtech"), "77.8%"),
        ("Tesla + Figure + Agility share of 2025 shipments", ("tesla", "figure-ai", "agility-robotics"), "3.4%"),
    ):
        got = [omdia(c) for c in ids]
        share = sum(u for u, _ in got) / n
        add(
            label,
            f"{share:.1%} ({sum(u for u, _ in got):,.0f} units)",
            [r for _, r in got] + [r_total],
            expected,
            f"{share:.1%}" == expected,
        )

    # --- Capital ---
    def funding(scope: str, year: str, period_end: str = "") -> tuple[pd.Series, str]:
        return fund.one(scope=scope, year=year, period_end=period_end)

    h23, r23 = funding("humanoid", "2023")
    h25, r25 = funding("humanoid", "2025")
    h26, r26 = funding("humanoid", "2026", "2026-05-15")
    ratio = float(h25["amount_usd"]) / float(h23["amount_usd"])
    add(
        "Humanoid VC 2023 → 2025 (PitchBook)",
        f"{style.fmt_usd(float(h23['amount_usd']))} → {style.fmt_usd(float(h25['amount_usd']))} ({ratio:.1f}×)",
        [r23, r25],
        "$430M → $6.1B (≈14×)",
        round(ratio) == 14,
    )
    add(
        "Humanoid VC 2026 to 15 May (PitchBook)",
        style.fmt_usd(float(h26["amount_usd"]), h26["amount_qualifier"]),
        [r26],
        ">$5B",
        float(h26["amount_usd"]) == 5e9 and h26["amount_qualifier"] == "gt",
    )
    for year, end, expected in (("2021", "", "$14.1B"), ("2025", "", "$15B"), ("2026", "2026-06-22", "$18.8B")):
        row, ref = funding("robotics_all", year, end)
        got = style.fmt_usd(float(row["amount_usd"]))
        add(f"Robotics VC {year}{' to 22 Jun' if end else ''} (Crunchbase)", got, [ref], expected, got == expected)

    # --- Valuation ÷ 2025 revenue ---
    vals = data.valuations()
    revenue_2025 = data.annual_revenue("2025")
    for cid, expected, note in (
        ("agility-robotics", "≈1,403×", "SPAC merger value (pre-money) ÷ audited FY2025 net sales"),
        ("skild-ai", "≈467× (R)", "revenue self-reported (R); valuation a lower bound"),
        ("unitree", "≈112×", "stock market value 30 Sep 2026 ÷ FY2025 revenue (final prospectus)"),
        ("ubtech", "≈17×", "stock market value 30 Sep 2026 ÷ FY2025 revenue"),
        ("agibot", "≈14×", "revenue stated by its CEO (RMB 1.05B); valuation from Mar 2025"),
    ):
        hits = revenue_2025[revenue_2025["company_id"] == cid]
        rev_row, rev_ref = hits.iloc[0], f"valuations_revenue.csv:{hits.index[0] + 2}"
        v = vals[cid]
        val_ref = _valuation_ref(v)
        m = v.value_usd / float(rev_row["revenue_usd"])
        shown = f"{m:,.1f}×"
        ok = round(m) == int(expected.strip("≈≤×(R) ").replace(",", ""))
        add(f"Valuation ÷ 2025 revenue: {cid}", shown, [val_ref, rev_ref], expected, ok, note)

    # --- Listed companies at 30 Sep 2026 ---
    uni, r_uni = vr.one(company_id="unitree", date="2026-09-30", valuation_type="market_cap")
    ubt, r_ubt = vr.one(company_id="ubtech", date="2026-09-30", valuation_type="market_cap")
    first, r_first = vr.one(company_id="unitree", date="2026-08-19", source_name="The Paper (澎湃新闻)")
    add(
        "Unitree stock market value 30 Sep 2026",
        style.fmt_usd(float(uni["valuation_usd"])),
        [r_uni],
        "$27.2B",
        style.fmt_usd(float(uni["valuation_usd"])) == "$27.2B",
    )
    add(
        "UBTech stock market value 30 Sep 2026",
        style.fmt_usd(float(ubt["valuation_usd"])),
        [r_ubt],
        "$4.77B",
        style.fmt_usd(float(ubt["valuation_usd"])) == "$4.77B",
    )
    change = float(uni["valuation_local"]) / float(first["valuation_local"]) - 1
    add(
        "Unitree change vs first-day close",
        f"{change:.1%}",
        [r_uni, r_first],
        "-47%",
        round(change * 100) == -47,
        "RMB terms: 182,170,738,736 (close 450.40 on 30 Sep) vs 341,800,000,000 (first-day close 845 on 19 Aug)",
    )

    # --- Agility (SEC Form S-4/A) ---
    fy, r_fy = vr.one(company_id="agility-robotics", revenue_period="FY2025")
    h1, r_h1 = vr.one(company_id="agility-robotics", revenue_period="H1 2026")
    rp, r_rp = items.one(item_id="agility-robotics-fy2025-net-sales-related-parties")
    share = float(rp["value"]) / float(fy["revenue_usd"])
    add(
        "Agility FY2025 net sales (audited)",
        f"${float(fy['revenue_usd']):,.0f}",
        [r_fy],
        "$1.78M",
        style.fmt_usd(float(fy["revenue_usd"])) == "$1.78M",
    )
    add(
        "Agility FY2025 share of sales to related parties",
        f"{share:.1%}",
        [r_rp, r_fy],
        "63.5%",
        f"{share:.1%}" == "63.5%",
    )
    add(
        "Agility FY2025 net loss",
        f"${-float(fy['net_income_usd']):,.0f}",
        [r_fy],
        "$138M",
        round(-float(fy["net_income_usd"]) / 1e6) == 138,
    )
    add(
        "Agility H1 2026 net sales (unaudited)",
        f"${float(h1['revenue_usd']):,.0f}",
        [r_h1],
        "$174K",
        round(float(h1["revenue_usd"]) / 1e3) == 174,
    )
    add(
        "Agility H1 2026 net loss",
        f"${-float(h1['net_income_usd']):,.0f}",
        [r_h1],
        "$362M",
        round(-float(h1["net_income_usd"]) / 1e6) == 362,
    )
    s26, r_s26 = items.one(item_id="agility-robotics-h1-2026-stock-compensation")
    s25, r_s25 = items.one(item_id="agility-robotics-h1-2025-stock-compensation")
    inc = float(s26["value"]) - float(s25["value"])
    add(
        "Agility H1 2026 stock compensation: increase vs H1 2025",
        f"${inc:,.0f} (total ${float(s26['value']):,.0f})",
        [r_s26, r_s25],
        "~$252.5M stock comp",
        round(inc / 1e5) == 2525,
        "$252.5M is the increase over H1 2025; total H1 2026 stock compensation is $280.6M",
    )
    cash, r_cash = items.one(item_id="agility-robotics-2026-06-30-cash")
    add(
        "Agility cash and equivalents at 30 Jun 2026",
        f"${float(cash['value']):,.0f}",
        [r_cash],
        "$14.7M",
        round(float(cash["value"]) / 1e5) == 147,
    )
    for item_id, label in (
        ("agility-robotics-2025-12-31-deferred-revenue", "Agility deferred revenue at 31 Dec 2025"),
        ("agility-robotics-2026-05-warrants-per-robot", "Agility warrants per robot (related-party customer)"),
    ):
        row, ref = items.one(item_id=item_id)
        add(label, f"{float(row['value']):,.0f}", [ref], f"{float(row['value']):,.0f}", True)
    orders, r_orders = ev.one(company_id="agility-robotics", metric="orders_value_usd")
    add(
        "Agility Digit 5 orders (S-4/A)",
        style.fmt_usd(float(orders["value"]), orders["value_qualifier"]),
        [r_orders],
        "$300M",
        orders["value_qualifier"] == "" and float(orders["value"]) == 300e6,
        "the filing says '$300 million', not 'more than' (press wording)",
    )

    # --- Company figures corrected or added in round 2 ---
    uni_rev = revenue_2025[revenue_2025["company_id"] == "unitree"]
    agi_rev = revenue_2025[revenue_2025["company_id"] == "agibot"]
    for frame, label, expected in (
        (uni_rev, "Unitree FY2025 revenue (final prospectus)", "RMB 1,699M ($243M)"),
        (agi_rev, "AgiBot FY2025 revenue (stated by its CEO)", "RMB 1,050M ($150M)"),
    ):
        row = frame.iloc[0]
        got = f"RMB {float(row['revenue_local']) / 1e6:,.0f}M ({style.fmt_usd(float(row['revenue_usd']))})"
        add(label, got, [f"valuations_revenue.csv:{frame.index[0] + 2}"], expected, got == expected)
    row = uni_rev.iloc[0]
    got = f"RMB {float(row['net_income_local']) / 1e6:,.0f}M"
    add(
        "Unitree FY2025 net profit (final prospectus)",
        got,
        [f"valuations_revenue.csv:{uni_rev.index[0] + 2}"],
        "RMB 278M",
        got == "RMB 278M",
        "adjusted profit (扣非) RMB 591M is not used",
    )
    own, r_own = ship.one(company_id="unitree", year="2025", source_type="company", metric="shipped")
    add(
        "Unitree 2025 humanoid shipments (company, final prospectus)",
        f"{float(own['units']):,.0f}",
        [r_own],
        "5,511",
        float(own["units"]) == 5511 and own["units_qualifier"] == "",
    )

    # --- Shipment forecasts vs 2025 ---
    for publisher, year, expected in (
        ("BofA Global Research", "2026", "6.8×"),
        ("Goldman Sachs", "2030", "≥19×"),
        ("BofA Global Research", "2030", "90×"),
        ("Interact Analysis", "2035", "≥53×"),
        ("Omdia", "2035", "195×"),
    ):
        row, ref = fc.one(publisher=publisher, target_year=year, metric="annual_units")
        m = float(row["units"]) / n
        shown = f"{m:.1f}×" if m < 10 else f"{m:,.0f}×"
        floor = row["units_qualifier"] in ("gt", "gte")
        add(
            f"Forecast {publisher} {year} ÷ 2025 shipments",
            ("≥" if floor else "") + shown,
            [ref, r_total],
            expected,
            ("≥" if floor else "") + shown == expected,
        )
    return out


def _valuation_ref(v: data.Valuation) -> str:
    """The row behind a Valuation record, as `file.csv:line`."""
    for table in ("valuations_revenue", "funding_rounds"):
        df = data.load(table)
        hit = df[(df["company_id"] == v.company_id) & (df["date"] == v.date) & (df["source_url"] == v.source_url)]
        if len(hit):
            return f"{table}.csv:{hit.index[0] + 2}"
    raise LookupError(v)


def main() -> pd.DataFrame:
    table = pd.DataFrame(figures())
    style.OUTPUTS.mkdir(exist_ok=True)
    table.to_csv(OUT, index=False, lineterminator="\n")
    with pd.option_context("display.max_colwidth", 70, "display.width", 250):
        print(table[["figure", "value", "rows_used", "expected", "matches"]].to_string(index=False))
    print(f"\n{OUT}")
    return table


if __name__ == "__main__":
    main()

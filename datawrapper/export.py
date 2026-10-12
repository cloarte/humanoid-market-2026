"""Write the exact CSV behind each Datawrapper chart, plus the colour notes.

Run:  python -m datawrapper.export      -> outputs/dw_*.csv and outputs/dw_colors.md

Text columns are written ready to read (e.g. '1.2M robots in 2030'), so the labels and tooltips in
Datawrapper need no formulas.
"""

from __future__ import annotations

import pandas as pd

from analysis import disclosure_scorecard
from charts import data
from src import style

COUNTRY_NAME = {"US": "United States", "CN": "China", "GB": "United Kingdom"}
COUNTRY_SHORT = {"US": "US", "CN": "China", "GB": "UK"}
DEAL_LABEL = {"in_talks": "in talks", "term_sheet": "term sheet"}
LOWER_BOUND = ("gt", "gte")
PUBLISHER_SHORT = {"BofA Global Research": "BofA"}
SHIPPED = "Shipped (Omdia estimate)"


def _usd(value: float | None, qualifier: str = "") -> str:
    return style.fmt_usd(value, qualifier) if value is not None else ""


def month(date: str) -> str:
    """'2025-09-16' or '2025-09' -> 'Sep 2025'. A bare year (or any other form) is kept as is."""
    if len(date) >= 7 and date[4] == "-" and date[5:7].isdigit():
        return pd.Timestamp(date[:7] + "-01").strftime("%b %Y")
    return date


def day(date: str) -> str:
    """'2026-09-30' -> '30 Sep 2026' (portable: no platform-specific strftime flags)."""
    ts = pd.Timestamp(date)
    return f"{ts.day} {ts:%b %Y}"


GROUPS = {"humanoid_fullstack": "Humanoid makers", "foundation_model": "Robot AI labs"}


VALUE_WORDS = {
    "Stock market value": "stock market value",
    "SPAC merger": "SPAC merger value",
    "Funding round": "funding-round value",
}


def value_source(v: data.Valuation, status: str) -> str:
    """Where a valuation comes from, in plain words. Pre/post-money detail stays in the data."""
    if v.basis == "market cap":
        return "Stock market value"
    return "SPAC merger" if status == "spac_pending" else "Funding round"


def valuation_type(v: data.Valuation, status: str) -> str:
    """Grey line under a company's name: 'Funding round – Sep 2025', 'Stock market value – 30 Sep 2026',
    'Funding round – Jan 2026 (at least)'."""
    when = day(v.date) if v.basis == "market cap" else month(v.date)
    return f"{value_source(v, status)} – {when}" + (" (at least)" if v.qualifier in LOWER_BOUND else "")


def valuations() -> pd.DataFrame:
    """Chart 3 (bars): latest valuation per company, grouped into humanoid makers and robot AI labs.

    'Label' carries the name (with * when the company has not confirmed the value) and, in grey,
    how and when the value was reported."""
    co = data.companies()
    rows = []
    for cid, v in data.valuations().items():
        c = co.loc[cid]
        name = c["name"] + ("*" if v.confidence != "V" else "")
        kind = valuation_type(v, c["status"])
        rows.append(
            {
                "Label": f'{name}<br><span style="opacity:0.6;font-size:12px">{kind}</span>',
                "Valuation ($B)": round(v.value_usd / 1e9, 2),
                "Country": COUNTRY_SHORT.get(c["country"], c["country"]),
                "Group": GROUPS[c["segment"]],
                "Company": c["name"],
                "Valuation type": kind,
                "Confirmed by the company": "yes" if v.confidence == "V" else "no",
                "Source": v.source_name,
            }
        )
    order = {g: i for i, g in enumerate(GROUPS.values())}
    frame = pd.DataFrame(rows)
    frame["_order"] = frame["Group"].map(order)
    return frame.sort_values(["_order", "Valuation ($B)"], ascending=[True, False]).drop(columns="_order")


def pending_deals() -> str:
    """'FieldAI $10B (term sheet, Oct 2026) · 1X Technologies ~$6B (in talks, Aug 2026) · ...'."""
    co = data.companies()
    pending = sorted(data.valuations(include_pending=True).values(), key=lambda v: -v.value_usd)
    deals = [
        f"{co.loc[v.company_id, 'name']} {_usd(v.value_usd, v.qualifier)} ({DEAL_LABEL[v.status]}, {month(v.date)})"
        for v in pending
    ]
    return " · ".join(deals)


def _multiple(v: data.Valuation, revenue: float, revenue_qualifier: str) -> str:
    """'Valued at 111× its 2025 revenue', bounded when either side is a lower bound."""
    m = f"{round(v.value_usd / revenue):,}×"
    val_floor, rev_floor = v.qualifier in LOWER_BOUND, revenue_qualifier in LOWER_BOUND
    if val_floor and not rev_floor:
        return f"Valued at {m} or more its 2025 revenue"
    if rev_floor and not val_floor:
        return f"Valued at up to {m} its 2025 revenue"
    return f"Valued at {'about ' if val_floor or v.qualifier == 'approx' else ''}{m} its 2025 revenue"


def valuation_vs_revenue() -> pd.DataFrame:
    """Chart 4 (scatter): companies with both a disclosed 2025 revenue and a valuation."""
    co = data.companies()
    vals = data.valuations()
    vr = data.annual_revenue("2025")
    rows = []
    for _, r in vr.iterrows():
        cid = r["company_id"]
        if cid not in vals:
            continue
        v = vals[cid]
        rev, rev_q = float(r["revenue_usd"]), r["revenue_qualifier"]
        when = "" if v.basis == "market cap" else f" ({month(v.date)})"
        caveats = []
        if r["confidence"] != "V":
            caveats.append("Revenue is self-reported.")
        if rev_q in LOWER_BOUND:
            caveats.append("Revenue is a lower bound.")
        if v.basis != "market cap" and data.fx.event_date(v.date).year < 2026:
            caveats.append(f"Latest valuation dates from {month(v.date)}.")
        rows.append(
            {
                "Company": co.loc[cid, "name"],
                "Country": COUNTRY_NAME.get(co.loc[cid, "country"], co.loc[cid, "country"]),
                "Revenue 2025 ($M)": round(rev / 1e6, 2),
                "Valuation ($B)": round(v.value_usd / 1e9, 2),
                "Valuation / revenue": round(v.value_usd / rev),
                "Headline": _multiple(v, rev, rev_q),
                "Detail": f"{_usd(v.value_usd, v.qualifier)} {VALUE_WORDS[value_source(v, co.loc[cid, 'status'])]}"
                f"{when} · {_usd(rev, rev_q)} revenue",
                "Caveat": " ".join(caveats),
                "Revenue source": r["source_name"],
                "Confidence": r["confidence"],
            }
        )
    return pd.DataFrame(rows).sort_values("Valuation / revenue", ascending=False)


def robots(n: float) -> str:
    """13,318 · 90k · 1.2M."""
    if n >= 1e6:
        return style.fmt_units(n, noun="")
    return f"{n / 1e3:,.0f}k" if n >= 20_000 else f"{n:,.0f}"


def shipment_forecasts() -> pd.DataFrame:
    """Chart 5 (scatter): humanoid robots shipped worldwide in 2025 (Omdia) and published forecasts of
    annual shipments. Unverified (U) forecasts are left out; each forecast is compared with 2025."""
    s = data.load("shipments")
    s = s[(s["company_id"] == "_all") & (s["year"] == "2025") & (s["data_provider"] == "Omdia")]
    base = float(s.iloc[0]["units"])
    rows = [
        {
            "Label": f"Shipped in 2025: {robots(base)}",
            "Year": 2025,
            "Robots per year": int(base),
            "Kind": SHIPPED,
            "Headline": f"{robots(base)} robots shipped in 2025",
            "Detail": "Omdia estimate, all makers",
        }
    ]
    f = data.load("forecasts")
    f = f[(f["metric"] == "annual_units") & (f["units"] != "") & (f["confidence"] != "U")]
    for _, r in f.iterrows():
        n, floor = float(r["units"]), r["units_qualifier"] in LOWER_BOUND
        times = n / base
        multiple = f"{times:.1f}" if times < 10 else f"{times:,.0f}"
        who = f"{r['publisher']} ({month(r['publish_date'])})" + (", base case" if r["scenario"] == "base" else "")
        rows.append(
            {
                "Label": f"{PUBLISHER_SHORT.get(r['publisher'], r['publisher'])} {'>' if floor else ''}{robots(n)}",
                "Year": int(r["target_year"]),
                "Robots per year": int(n),
                "Kind": "Forecast",
                "Headline": f"{'Over ' if floor else ''}{robots(n)} robots in {r['target_year']}",
                "Detail": f"{multiple} times 2025{' or more' if floor else ''} · {who}",
            }
        )
    return pd.DataFrame(rows).sort_values(["Year", "Robots per year"])


SYMBOL_STYLE = {
    disclosure_scorecard.YES: f'<b style="color:{style.INK}">✓</b>',
    disclosure_scorecard.PARTIAL: f'<span style="color:{style.INK}">◐</span>',
    disclosure_scorecard.NO: f'<span style="color:{style.SLATE_LIGHT}">✗</span>',
}


def scorecard_table() -> pd.DataFrame:
    """Chart 6 (table): company (country in grey below) and one styled symbol per item."""
    table = disclosure_scorecard.wide(disclosure_scorecard.scorecard())
    table["Company"] = [
        f'{name}<br><span style="opacity:0.6;font-size:12px">{country}</span>'
        for name, country in zip(table["Company"], table["Country"], strict=True)
    ]
    symbols = table.drop(columns=["Company", "Country"]).apply(lambda col: col.map(SYMBOL_STYLE))
    return pd.concat([table[["Company"]], symbols], axis=1)


DATASETS = {
    "dw_03_valuations": valuations,
    "dw_04_val_rev": valuation_vs_revenue,
    "dw_05_shipment_forecasts": shipment_forecasts,
    "dw_06_disclosure_scorecard": scorecard_table,
}


def colors_note() -> str:
    lines = ["# Datawrapper colours", "", "Paste these hex codes in each chart (Refine > Colors).", ""]
    lines += [f"- {name}: `{hexcode}`" for name, hexcode in style.DATAWRAPPER_COLORS.items()]
    lines += ["", "Background and fonts come from the Datawrapper theme (custom themes are a paid add-on)."]
    return "\n".join(lines) + "\n"


def main() -> None:
    style.OUTPUTS.mkdir(exist_ok=True)
    for name, build in DATASETS.items():
        path = style.OUTPUTS / f"{name}.csv"
        build().to_csv(path, index=False, lineterminator="\n")
        print(path)
    path = style.OUTPUTS / "dw_colors.md"
    path.write_text(colors_note(), encoding="utf-8", newline="\n")
    print(path)


if __name__ == "__main__":
    main()

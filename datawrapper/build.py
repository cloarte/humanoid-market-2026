"""Create or update the Datawrapper charts as unpublished drafts in the account of the token's owner.

Run:  python -m datawrapper.build                  create/update every chart from outputs/dw_*.csv
      python -m datawrapper.build --preview DIR    also save a server-rendered PNG of each draft in DIR

Charts are never published by this script: review them in Datawrapper and publish there.
Chart and folder ids are kept in datawrapper/charts.json so re-runs update the same charts.
Scatter-plot property names follow the official Python client (chekos/Datawrapper, charts/scatter.py).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from analysis import disclosure_scorecard as scorecard
from datawrapper import client, export
from src import style

STATE = Path(__file__).resolve().parent / "charts.json"
FOLDER = "Physical AI by the Numbers #1"
REPO = "https://github.com/cloarte/humanoid-market-2026"
BYLINE = "XBayAmauta"
COUNTRY_COLORS = {"China": style.AMBER, "United States": style.SLATE, "United Kingdom": style.OTHER}


def col(name: str) -> str:
    """Placeholder for a column in a Datawrapper tooltip: lowercase, non-alphanumerics to underscores."""
    return "{{ " + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") + " }}"


def notes(*lines: str) -> str:
    """Chart notes as short upright lines, one idea per line (Datawrapper renders this HTML)."""
    return '<span style="font-style:normal;font-size:13px;line-height:1.5">' + "<br>".join(lines) + "</span>"


def term(name: str, text: str) -> str:
    return f"<b>{name}</b> {text}"


def labels_of(dataset: str, column: str) -> list[str]:
    """Every value of `column`, so each point gets a label (these charts have few points)."""
    with (style.OUTPUTS / f"{dataset}.csv").open(encoding="utf-8") as f:
        return [row[column] for row in csv.DictReader(f)]


def scatter(x_range: list, y_range: list, colors: dict, tooltip: tuple[str, str], labels: list[str]) -> dict:
    """Log-log scatter settings: no vertical grid, numbers on both axes, every point labelled."""
    return {
        "x-axis": {"log": True, "range": x_range, "ticks": []},
        "y-axis": {"log": True, "range": y_range, "ticks": []},
        "x-format": "0,0.[00]",
        "y-format": "0,0.[0]",
        "x-grid-lines": "just-labels",
        "y-grid-lines": "on",
        "color-by-column": True,
        "color-category": {"map": colors},
        "show-color-key": True,
        "size": "fixed",
        "fixed-size": 9,
        "opacity": 1,
        "auto-labels": True,
        "add-labels": labels,
        "tooltip": {"title": tooltip[0], "body": tooltip[1], "enabled": True, "sticky": False, "migrated": True},
    }


def specs() -> dict:
    """Chart settings, built at run time because labels come from the freshly exported CSVs."""
    val_rev_tooltip = (
        col("Company"),
        f'<b>{col("Headline")}</b><br>{col("Detail")}<br><span style="color:{style.INK_MUTED}">{col("Caveat")}</span>',
    )
    return {
        "dw_03_valuations": {
            "type": "d3-bars",
            "title": "Figure AI leads; Unitree is China's only company above $5B",
            "intro": "Latest valuation, US$ billions. Under each name: where the value comes from, and its date.",
            "alt": "Bar chart of the latest valuation of 14 humanoid robot makers and robot AI labs, grouped by "
            "type and coloured by country. Figure AI leads at $39 billion, followed by Unitree at $27.2 billion "
            "(stock market value); Skild AI and Physical Intelligence lead the AI labs at $14 billion and "
            "$11.2 billion.",
            "notes": notes(
                term("Funding round:", "the company's value implied by its latest investment round."),
                term("Stock market value:", "share price × shares on 30 Sep 2026."),
                term("SPAC merger:", "value agreed for going public through a listed shell company."),
                term("(at least):", "the source gives a minimum.") + " " + term("*", "Not confirmed by the company."),
                term("Robot AI labs:", "build AI models for robots, not robots."),
                term("Not shown, deals not closed:", export.pending_deals() + "."),
            ),
            "axes": {"bars": "Valuation ($B)", "labels": "Label", "colors": "Country", "groups": "Group"},
            "column-format": {
                "Label": {"type": "text"},
                "Valuation ($B)": {"type": "number", "number-prepend": "$", "number-append": "B"},
            },
            "visualize": {
                "show-value-labels": True,
                "value-label-format": "0.0",
                "group-by-column": True,
                "show-group-labels": True,
                "sort-bars": False,
                "color-by-column": True,
                "color-category": {"map": {"US": style.SLATE, "China": style.AMBER, "UK": style.OTHER}},
                "show-color-key": True,
                "background": False,
            },
        },
        "dw_04_val_rev": {
            "type": "d3-scatter-plot",
            "title": "Valuation vs revenue",
            "alt": "Scatter chart of 2025 revenue against latest valuation for five companies, both on "
            "logarithmic scales. Agility is valued at about 1,400 times its $1.8 million revenue, Skild AI at "
            "467 times or more, Unitree at 111 times, UBTech at 17 times and AgiBot at up to 14 times.",
            "intro": "Companies with a disclosed 2025 revenue: revenue in US$ millions (horizontal) and "
            "valuation in US$ billions (vertical). Both axes logarithmic.",
            "notes": notes(
                term(
                    "Revenue 2025:",
                    "audited or from filings, except Skild AI (self-reported) and AgiBot (stated by its CEO).",
                ),
                term("Valuation:", "latest funding round, SPAC merger value, or stock market value on 30 Sep 2026."),
            ),
            "axes": {"x": "Revenue 2025 ($M)", "y": "Valuation ($B)", "color": "Country", "labels": "Company"},
            "visualize": scatter(
                [1, 500], [1, 50], COUNTRY_COLORS, val_rev_tooltip, labels_of("dw_04_val_rev", "Company")
            ),
        },
        "dw_05_shipment_forecasts": {
            "type": "d3-scatter-plot",
            # 2035 forecasts are 53 and 195 times the 2025 figure (outputs/dw_05_shipment_forecasts.csv).
            "title": "Forecasts assume 50 to 200 times more robots by 2035",
            "alt": "Scatter chart of humanoid robots shipped per year: 13,318 in 2025 by Omdia's estimate, "
            "against forecasts of 90,000 in 2026 (BofA), 250,000 to 1.2 million in 2030 (Goldman Sachs, BofA) "
            "and 700,000 to 2.6 million in 2035 (Interact Analysis, Omdia).",
            "intro": "Humanoid robots shipped worldwide per year: the 2025 estimate and published forecasts. "
            "Logarithmic scale.",
            "notes": notes(
                term("&gt;", "marks a lower bound, as published.") + " " + term("Goldman Sachs:", "base case."),
                term("Caution:", "forecasts come from different publishers and dates; definitions may differ."),
            ),
            "axes": {"x": "Year", "y": "Robots per year", "color": "Kind", "labels": "Label"},
            "column-format": {"Year": {"type": "number"}},
            "visualize": {
                **scatter(
                    [2024, 2036],
                    [5000, 5_000_000],
                    {export.SHIPPED: style.AMBER, "Forecast": style.SLATE},
                    (col("Headline"), col("Detail")),
                    labels_of("dw_05_shipment_forecasts", "Label"),
                ),
                "x-axis": {"log": False, "range": [2024, 2036], "ticks": [2025, 2026, 2030, 2035]},
                "x-format": "0",
                "y-format": "0,0",
            },
        },
        "dw_06_disclosure_scorecard": scorecard_spec(),
    }


def scorecard_spec() -> dict:
    """Table settings for the disclosure scorecard; title and alt text are computed from the table."""
    long = scorecard.scorecard()
    work = long[long["item"] == "paid_deployment"]
    # Only a full disclosure counts here: a ◐ is a press count or a partial figure, not the company saying it.
    n, yes = work["company_id"].nunique(), int((work["status"] == scorecard.YES).sum())
    title = (
        "No humanoid maker says how many robots do paid work"
        if yes == 0
        else f"Only {yes} of {n} humanoid makers say how many robots do paid work"
    )
    headers = [header for header, _, _ in scorecard.COLUMNS.values()]
    return {
        "type": "tables",
        "title": title,
        "alt": f"Table of what {n} humanoid robot makers publicly disclose as of 12 October 2026. "
        + " ".join(scorecard.summary(long).values()),
        "intro": f"What {n} humanoid makers publicly disclose about their robots, as of 12 Oct 2026. "
        "✓ disclosed · ◐ partial · ✗ not found",
        "notes": notes(
            term("Units:", "robots shipped or sold in a year.")
            + " "
            + term("At work:", "how many robots work for paying customers, excluding pilots."),
            term("Hours:", "operating hours at customers.")
            + " "
            + term("Customer:", "a purchase, order or commercial agreement (pilots included) with a named customer."),
            term("Rel. party:", "sales to related parties disclosed.")
            + " "
            + term("Audited:", "listed, or audited statements filed."),
            term("◐ partial:", "stated as a bound, self-reported, pilot only, a subsidiary only, or a press report.")
            + " "
            + term("✗:", "not found in public sources reviewed. Third-party estimates never count."),
            term("An audit of disclosure,", "not a ranking of quality. Evidence for every cell is in the dataset."),
        ),
        "column-format": {"Company": {"type": "text"}},
        "visualize": {
            "searchable": False,
            "sortTable": False,
            "perPage": 12,
            "columns": {h: {"alignment": "center"} for h in headers},
        },
    }


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def ensure_folder(state: dict) -> int:
    if "folder_id" not in state:
        state["folder_id"] = client.request("POST", "/folders", {"name": FOLDER})["id"]
        save_state(state)
    return state["folder_id"]


def metadata(spec: dict) -> dict:
    describe = {
        "intro": spec["intro"],
        "aria-description": spec["alt"],
        "byline": BYLINE,
        "source-name": "humanoid-market-2026 dataset",
        "source-url": REPO,
    }
    describe["number-format"] = "-"  # chart-wide format off: tables format per column (n1 = one decimal)
    meta = {
        "describe": describe,
        "annotate": {"notes": spec["notes"]},
        "publish": {"blocks": {"get-the-data": True}},
        "visualize": {"color-category": {"map": COUNTRY_COLORS}, **spec.get("visualize", {})},
    }
    if "column-format" in spec:
        meta["data"] = {"column-format": spec["column-format"]}
    if "axes" in spec:
        meta["axes"] = spec["axes"]
    return meta


def build(preview: Path | None = None) -> None:
    state = load_state()
    folder = ensure_folder(state)
    for name, spec in specs().items():
        csv_text = (style.OUTPUTS / f"{name}.csv").read_text(encoding="utf-8")
        chart_id = state.get("charts", {}).get(name)
        if chart_id is None:
            body = {"title": spec["title"], "type": spec["type"], "folderId": folder}
            chart_id = client.request("POST", "/charts", body)["id"]
            state.setdefault("charts", {})[name] = chart_id
            save_state(state)
        client.request("PUT", f"/charts/{chart_id}/data", csv_text)
        body = {"title": spec["title"], "type": spec["type"], "metadata": metadata(spec)}
        client.request("PATCH", f"/charts/{chart_id}", body)
        print(f"{name}: https://app.datawrapper.de/chart/{chart_id}/visualize (draft, not published)")
        if preview:
            png = client.download(f"/charts/{chart_id}/export/png?unit=px&mode=rgb&width=900&plain=false&zoom=2")
            (preview / f"{name}.png").write_bytes(png)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preview", type=Path, metavar="DIR", help="save a PNG render of each draft in DIR")
    args = parser.parse_args()
    export.main()
    build(preview=args.preview)


if __name__ == "__main__":
    main()

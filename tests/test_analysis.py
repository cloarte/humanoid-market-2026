"""Derived figures: every figure the article cites is recomputed from data/ with its source rows."""

from __future__ import annotations

from analysis import article_figures, valuation_per_unit
from analysis import disclosure_scorecard as sc


def test_article_figures_trace_to_rows():
    rows = article_figures.figures()
    assert len(rows) >= 30
    for r in rows:
        assert r["rows_used"], r["figure"]
        assert all(".csv:" in ref for ref in r["rows_used"].split("; ")), r["rows_used"]


def test_every_article_figure_reproduces():
    """The article brief's figures (v2) all reproduce from data/; a difference shows up as 'NO'."""
    flagged = [r["figure"] for r in article_figures.figures() if r["matches"] == "NO"]
    assert flagged == []


def test_valuation_per_unit_scope_and_values():
    t = valuation_per_unit.table().set_index("company_id")
    assert set(t.index) == {"figure-ai", "agility-robotics", "unitree", "ubtech", "agibot"}
    per_unit = t["valuation_per_unit_usd"]
    assert per_unit["figure-ai"] == 260_000_000
    assert round(per_unit["unitree"] / 1e6, 1) == 6.5
    assert t.loc["unitree", "company_units_bound"] == "exact"  # 5,511 per the final prospectus
    assert round(t.loc["unitree", "valuation_per_unit_company_units_usd"] / 1e6, 2) == 4.93
    assert all("Order of magnitude, not a multiple" in c for c in t["caveat"])


def test_scorecard_cells_have_evidence():
    long = sc.scorecard()
    assert long["company_id"].nunique() == len(sc.SCOPE)
    assert set(long["status"]) <= {sc.YES, sc.PARTIAL, sc.NO}
    shown = long[(long["status"] != sc.NO) & (long["item"] != "audited")]
    assert (shown["evidence_rows"] != "").all(), shown[shown["evidence_rows"] == ""]
    assert (long[long["status"] == sc.NO]["note"] != "").all()


def test_scorecard_ignores_third_party_estimates():
    """Omdia's 150-unit estimates must not count as a company disclosure of units."""
    long = sc.scorecard().set_index(["company_id", "item"])
    for cid in ("figure-ai", "agility-robotics", "tesla"):
        assert long.loc[(cid, "units"), "status"] == sc.NO


def test_scorecard_summary_is_computed():
    lines = sc.summary(sc.scorecard())
    assert set(lines) == set(sc.COLUMNS)
    assert all(f" of {len(sc.SCOPE)} humanoid makers " in line for line in lines.values())

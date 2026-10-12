"""The validator must pass on the committed data and catch each kind of error it promises to catch."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

from src import schema
from src.validate import Report, check_repo, validate_data

SOURCE = {
    "source_url": "https://example.com/a",
    "source_name": "Example",
    "source_date": "2026-01-05",
    "accessed_date": "2026-01-06",
    "confidence": "V",
}
COMPANY = {"company_id": "acme", "name": "Acme", "country": "US", "segment": "humanoid_fullstack", "status": "private"}
FX_ROW = {
    "date": "2026-03-02",
    "currency": "CNY",
    "rate": "7.1",
    "series_id": "DEXCHUS",
    "source_url": "https://fred.stlouisfed.org/series/DEXCHUS",
    "source_name": "FRB",
}


def write_dataset(folder: Path, rows: dict[str, list[dict]]) -> Path:
    """Write every table (header only unless rows are given) into `folder`."""
    for table in schema.TABLES:
        cols = schema.columns(table)
        with (folder / f"{table}.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
            writer.writeheader()
            for row in rows.get(table, []):
                base = SOURCE if table != "fx_rates" else {}
                writer.writerow({c: "" for c in cols} | {k: v for k, v in base.items() if k in cols} | row)
    return folder


def errors_for(tmp_path: Path, table: str, row: dict) -> list[str]:
    rows = {"companies": [COMPANY], "fx_rates": [FX_ROW]}
    rows.setdefault(table, []).append(row)
    rep, _ = validate_data(write_dataset(tmp_path, rows))
    return rep.errors


def test_committed_data_is_valid():
    rep, frames = validate_data()
    check_repo(rep)
    assert rep.errors == []
    assert len(frames["companies"]) > 0


def test_minimal_valid_dataset(tmp_path):
    rep, _ = validate_data(write_dataset(tmp_path, {"companies": [COMPANY], "fx_rates": [FX_ROW]}))
    assert rep.errors == []


EVIDENCE = {
    "company_id": "acme",
    "stage": "pilot",
    "metric": "operating_hours",
    "unit": "hours",
    "as_of": "2025",
    "verification": "company_statement",
}
ROUND = {
    "round_id": "acme-2026-03-seed",
    "company_id": "acme",
    "date": "2026-03",
    "round_type": "seed",
    "status": "closed",
}


@pytest.mark.parametrize(
    ("table", "row", "expected"),
    [
        ("companies", COMPANY | {"company_id": "Bad_ID"}, "not a valid slug"),
        ("companies", COMPANY | {"company_id": "acme2", "country": "USA"}, "ISO 3166-1"),
        ("companies", COMPANY | {"company_id": "acme3", "status": "public"}, "needs `ticker` and `exchange`"),
        ("funding_rounds", ROUND | {"status": "in_talks"}, "in_talks` cannot have `confidence = V"),
        ("funding_rounds", ROUND | {"round_type": "series_z"}, "not a valid enum"),
        ("funding_rounds", ROUND | {"date": "2999-01"}, "in the future"),
        ("funding_rounds", ROUND | {"company_id": "ghost"}, "not in companies.csv"),
        ("funding_rounds", ROUND | {"amount_local": "100"}, "`currency` is blank"),
        ("funding_rounds", ROUND | {"amount_local": "100", "currency": "USD"}, "`amount_usd` is blank"),
        (
            "funding_rounds",
            ROUND
            | {
                "amount_local": "710",
                "currency": "CNY",
                "amount_usd": "200",
                "fx_rate": "7.1",
                "fx_date": "2026-03-02",
            },
            "amount_local/fx_rate = 100",
        ),
        (
            "funding_rounds",
            ROUND
            | {"amount_local": "700", "currency": "CNY", "amount_usd": "100", "fx_rate": "7", "fx_date": "2026-03-03"},
            "no CNY rate for 2026-03-03",
        ),
        ("funding_rounds", ROUND | {"source_url": "ftp://x"}, "not a valid URL"),
        ("funding_rounds", ROUND | {"source_date": "2026/01/05"}, "not a valid date"),
        ("funding_rounds", ROUND | {"accessed_date": "2026-01-01"}, "`accessed_date` before `source_date`"),
        ("funding_rounds", ROUND | {"amount_qualifier": "gt"}, "set but"),
        (
            "shipments",
            {"company_id": "acme", "year": "2025", "period": "FY", "metric": "shipped", "source_type": "company"},
            "put the source's wording in `units_text`",
        ),
        (
            "shipments",
            {
                "company_id": "acme",
                "year": "2025",
                "period": "FY",
                "units": "-5",
                "metric": "shipped",
                "source_type": "company",
            },
            "integer ≥ 0",
        ),
        (
            "shipments",
            {
                "company_id": "acme",
                "year": "2025",
                "period": "FY",
                "units": "5",
                "metric": "shipped",
                "source_type": "third_party",
            },
            "need `data_provider`",
        ),
        (
            "shipments",
            {
                "company_id": "acme",
                "year": "2025",
                "period": "cumulative",
                "units": "5",
                "metric": "shipped",
                "source_type": "company",
            },
            "needs `as_of`",
        ),
        ("valuations_revenue", {"company_id": "acme", "date": "2025"}, "no valuation, revenue or net income"),
        (
            "sector_funding",
            {"year": str(date.today().year), "scope": "humanoid", "amount_usd": "1", "data_provider": "X"},
            "must set `period_end`",
        ),
        (
            "forecasts",
            {
                "publisher": "X",
                "publish_date": "2026",
                "target_year": "2030",
                "metric": "annual_units",
                "scope_definition": "x",
            },
            "needs `units`",
        ),
        (
            "prices_bom",
            {
                "company_id": "_generic_cn",
                "product": "p",
                "product_class": "generic",
                "year": "2025",
                "value_usd": "9",
                "value_qualifier": "range",
                "kind": "bom_estimate",
            },
            "needs `value_usd_high`",
        ),
        (
            "deployment_evidence",
            EVIDENCE,
            "put the source's wording in `value_text`",
        ),
        (
            "deployment_evidence",
            EVIDENCE | {"value": "5", "metric": "orders_value_usd"},
            "must have `unit = USD`",
        ),
    ],
)
def test_catches_error(tmp_path, table, row, expected):
    errors = errors_for(tmp_path, table, row)
    assert any(expected in e for e in errors), errors


def test_duplicates_are_errors(tmp_path):
    rows = {"companies": [COMPANY, COMPANY], "fx_rates": [FX_ROW]}
    rep, _ = validate_data(write_dataset(tmp_path, rows))
    assert any("exact duplicate" in e for e in rep.errors)


def test_repo_policies(tmp_path):
    (tmp_path / "charts").mkdir()
    hex_colour = "#" + "FF0000"  # built at runtime so this test file itself passes the policy
    (tmp_path / "charts" / "bad.py").write_text(f'COLOR = "{hex_colour}"\n', encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "x.csv").write_text("notes\nCaterpillar dozer\n", encoding="utf-8")
    rep = Report()
    check_repo(rep, root=tmp_path)
    joined = "\n".join(rep.errors)
    assert "hex colour" in joined
    assert "Caterpillar" in joined
    assert "DATA_DICTIONARY.md" in joined


FIN_ITEM = {
    "item_id": "acme-fy2025-cash",
    "company_id": "acme",
    "period": "2025-12-31",
    "item": "cash_and_equivalents",
    "value": "14651873",
    "unit": "USD",
    "quote_text": "Cash and cash equivalents $ 14,651,873",
    "page_or_section": "p. F-71, Balance Sheets",
}


def test_financial_item_valid(tmp_path):
    assert errors_for(tmp_path, "company_financial_items", FIN_ITEM) == []


@pytest.mark.parametrize(
    "change, message",
    [
        ({"value": "14651874"}, "is not printed in `quote_text`"),
        ({"page_or_section": "F-71"}, "must start with 'p. '"),
        ({"item": "going_concern_auditor"}, "quoted statements have a blank `value`"),
    ],
)
def test_financial_item_errors(tmp_path, change, message):
    errors = errors_for(tmp_path, "company_financial_items", FIN_ITEM | change)
    assert any(message in e for e in errors), errors

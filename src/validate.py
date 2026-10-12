"""Schema and integrity checks for data/*.csv.

Usage:  python -m src.validate        (exit code 1 on any error)

Data checks (`validate_data`): required columns, types and enums, ISO dates, non-negative
numbers, source URLs, foreign keys to companies.csv, `in_talks` never `V`, FX consistency
against data/fx_rates.csv, duplicates, and per-table rules.

Repo checks (`check_repo`): DATA_DICTIONARY.md is up to date, no hex colours outside
src/style.py, no Caterpillar data.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from collections.abc import Callable
from datetime import date
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src import schema

ROOT = schema.ROOT
DATA = ROOT / "data"
TODAY = date.today()
FX_TOLERANCE = 0.005  # stored USD may differ from local / fx_rate by 0.5% (rounding)

RE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
RE_ISO2 = re.compile(r"^[A-Z]{2}$")
RE_CCY = re.compile(r"^[A-Z]{3}$")
RE_YEAR = re.compile(r"^(19\d\d|20\d\d|2100)$")
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_PDATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
RE_INT = re.compile(r"^-?\d+$")
RE_NUM = re.compile(r"^-?\d+(\.\d+)?$")
RE_HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")


class Report:
    """Collects errors (fail the run) and warnings (printed only)."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @staticmethod
    def _fmt(where: str, line: int | None, msg: str) -> str:
        return f"{where}{f':{line}' if line else ''}: {msg}"

    def error(self, where: str, line: int | None, msg: str) -> None:
        self.errors.append(self._fmt(where, line, msg))

    def warn(self, where: str, line: int | None, msg: str) -> None:
        self.warnings.append(self._fmt(where, line, msg))


# --- Cell helpers ----------------------------------------------------------------


def blank(v: str) -> bool:
    return v.strip() == ""


def num(v: str) -> float | None:
    """Parsed number, or None when blank or malformed (malformed cells are reported by check_cells)."""
    return float(v) if RE_NUM.match(v.strip()) else None


def parse_pdate(v: str) -> date:
    """Earliest calendar date of a (possibly reduced-precision) ISO date. Raises ValueError if invalid."""
    parts = [int(p) for p in v.split("-")]
    year, month, day = [*parts, 1, 1][:3]
    return date(year, month, day)


def line_of(index: int) -> int:
    """CSV line number of a dataframe row (line 1 is the header)."""
    return int(index) + 2


# --- Generic checks ----------------------------------------------------------------


def load(data_dir: Path, table: str, rep: Report) -> pd.DataFrame | None:
    path = data_dir / f"{table}.csv"
    if not path.exists():
        rep.error(table, None, f"missing file {path.name}")
        return None
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    df.columns = [c.strip() for c in df.columns]
    expected = schema.columns(table)
    missing = [c for c in expected if c not in df.columns]
    extra = [c for c in df.columns if c not in expected]
    if missing:
        rep.error(table, None, f"missing columns: {missing}")
    if extra:
        rep.error(table, None, f"unexpected columns (add them to src/schema.py first): {extra}")
    return None if missing else df


def is_valid(col: schema.Col, v: str) -> bool:
    if col.kind == "id":
        return bool(RE_ID.match(v)) or (col.name == "company_id" and v in schema.RESERVED_COMPANY_IDS)
    if col.kind == "enum":
        return v in col.enum
    if col.kind == "url":
        return v.startswith(("http://", "https://")) and " " not in v
    if col.kind in ("date", "pdate"):
        if not (RE_DATE if col.kind == "date" else RE_PDATE).match(v):
            return False
        try:
            parse_pdate(v)
        except ValueError:
            return False
        return True
    if col.kind in ("int", "num"):
        rx = RE_INT if col.kind == "int" else RE_NUM
        return bool(rx.match(v)) and (col.signed or float(v) >= 0)
    rx = {"iso2": RE_ISO2, "ccy": RE_CCY, "year": RE_YEAR}.get(col.kind)
    return bool(rx.match(v)) if rx else True  # free text


def check_cells(table: str, df: pd.DataFrame, rep: Report) -> None:
    for col in schema.TABLES[table]["cols"]:
        for i, raw in df[col.name].items():
            v = raw.strip()
            if not v:
                if col.required:
                    rep.error(table, line_of(i), f"`{col.name}` is required")
                continue
            if v != raw:
                rep.error(table, line_of(i), f"`{col.name}` has leading/trailing whitespace")
            if not is_valid(col, v):
                allowed = f" (allowed: {', '.join(col.enum)})" if col.kind == "enum" else ""
                rep.error(
                    table, line_of(i), f"`{col.name}` = {v!r} is not a valid {schema.KIND_DOC[col.kind]}{allowed}"
                )


def check_duplicates(table: str, df: pd.DataFrame, rep: Report) -> None:
    for i in df[df.duplicated(keep="first")].index:
        rep.error(table, line_of(i), "exact duplicate of an earlier row")
    key = schema.TABLES[table]["key"]
    for i in df[df.duplicated(subset=key, keep="first")].index:
        rep.error(table, line_of(i), f"duplicate key ({', '.join(key)})")


def check_qualifiers(table: str, df: pd.DataFrame, rep: Report) -> None:
    for qcol, (targets, high) in schema.QUALIFIER_TARGETS.get(table, {}).items():
        for i, r in df.iterrows():
            q = r[qcol]
            if q and all(blank(r[t]) for t in targets):
                rep.error(table, line_of(i), f"`{qcol}` set but {targets} are blank")
            if q == "range" and high is None:
                rep.error(table, line_of(i), f"`{qcol} = range` is not allowed in this table")
            if q == "range" and high and blank(r[high]):
                rep.error(table, line_of(i), f"`{qcol} = range` needs `{high}`")
            if high and not blank(r[high]):
                low_v, high_v = num(r[targets[0]]), num(r[high])
                if q != "range":
                    rep.error(table, line_of(i), f"`{high}` only allowed with `{qcol} = range`")
                elif low_v is not None and high_v is not None and high_v < low_v:
                    rep.error(table, line_of(i), f"`{high}` is below `{targets[0]}`")


def check_fx(table: str, df: pd.DataFrame, rates: dict[tuple[str, str], float], rep: Report) -> None:
    """Every non-USD amount needs a USD twin equal to local / fx_rate, using a rate from fx_rates.csv."""
    for i, r in df.iterrows():
        needs_rate = False
        for local, ccy, usd in schema.FX_TRIPLES[table]:
            if blank(r[local]):
                continue
            if blank(r[ccy]) or blank(r[usd]):
                missing = ccy if blank(r[ccy]) else usd
                rep.error(table, line_of(i), f"`{local}` present but `{missing}` is blank")
                continue
            local_v, usd_v = num(r[local]), num(r[usd])
            if local_v is None or usd_v is None:
                continue  # malformed number, reported by check_cells
            if r[ccy] == "USD":
                if local_v != usd_v:
                    rep.error(table, line_of(i), f"`{ccy}` is USD but `{local}` != `{usd}`")
                continue
            needs_rate = True
            rate = num(r["fx_rate"])
            if not rate or blank(r["fx_date"]):
                continue  # reported once below
            implied = local_v / rate
            if abs(implied - usd_v) > FX_TOLERANCE * max(abs(usd_v), 1.0):
                rep.error(table, line_of(i), f"`{usd}` = {usd_v:,.0f} but {local}/fx_rate = {implied:,.0f}")
            ref = rates.get((r["fx_date"], r[ccy]))
            if ref is None:
                rep.error(table, line_of(i), f"no {r[ccy]} rate for {r['fx_date']} in data/fx_rates.csv")
            elif abs(ref - rate) > 1e-9:
                rep.error(table, line_of(i), f"`fx_rate` {r['fx_rate']} != fx_rates.csv value {ref} on {r['fx_date']}")
        has_rate = not (blank(r["fx_rate"]) and blank(r["fx_date"]))
        if needs_rate and (blank(r["fx_rate"]) or blank(r["fx_date"])):
            rep.error(table, line_of(i), "non-USD amount needs `fx_rate` and `fx_date`")
        if has_rate and not needs_rate:
            rep.warn(table, line_of(i), "`fx_rate`/`fx_date` set but nothing is converted")


def check_not_future(table: str, df: pd.DataFrame, cols: list[str], rep: Report) -> None:
    for col in cols:
        for i, v in df[col].items():
            if RE_PDATE.match(v):
                try:
                    if parse_pdate(v) > TODAY:
                        rep.error(table, line_of(i), f"`{col}` {v} is in the future")
                except ValueError:
                    pass  # reported by check_cells


def check_sources(table: str, df: pd.DataFrame, rep: Report) -> None:
    check_not_future(table, df, ["source_date", "accessed_date"], rep)
    for i, r in df.iterrows():
        if (
            RE_DATE.match(r["source_date"])
            and RE_DATE.match(r["accessed_date"])
            and r["accessed_date"] < r["source_date"]
        ):
            rep.error(table, line_of(i), "`accessed_date` before `source_date`")


def check_foreign_keys(frames: dict[str, pd.DataFrame], rep: Report) -> None:
    known = set(frames["companies"]["company_id"]) | set(schema.RESERVED_COMPANY_IDS)
    for table, df in frames.items():
        if table == "companies" or "company_id" not in df.columns:
            continue
        for i, v in df["company_id"].items():
            if v and v not in known:
                rep.error(table, line_of(i), f"company_id {v!r} not in companies.csv")


# --- Per-table rules -------------------------------------------------------------


def rules_companies(df: pd.DataFrame, rep: Report) -> None:
    for i, r in df.iterrows():
        if r["status"] == "public" and (blank(r["ticker"]) or blank(r["exchange"])):
            rep.error("companies", line_of(i), "public company needs `ticker` and `exchange`")
        if r["company_id"] in schema.RESERVED_COMPANY_IDS:
            rep.error("companies", line_of(i), "reserved ids cannot be defined in companies.csv")


def rules_funding_rounds(df: pd.DataFrame, rep: Report) -> None:
    t = "funding_rounds"
    for i, r in df.iterrows():
        if r["status"] == "in_talks" and r["confidence"] == "V":
            rep.error(t, line_of(i), "`status = in_talks` cannot have `confidence = V`")
        if r["status"] == "term_sheet" and r["confidence"] == "V":
            rep.warn(t, line_of(i), "`term_sheet` row marked `V`; is the term sheet itself public?")
        if not blank(r["amount_usd"]) and blank(r["amount_local"]):
            rep.error(t, line_of(i), "`amount_local` (+ `currency`) must be present when `amount_usd` is")
        post, pre = num(r["post_money_usd"]), num(r["pre_money_usd"])
        if post is not None and pre is not None and post < pre:
            rep.error(t, line_of(i), "`post_money_usd` < `pre_money_usd`")
    check_not_future(t, df, ["date"], rep)
    for rid, g in df.groupby("round_id"):
        if g["company_id"].nunique() > 1:
            rep.error(t, line_of(g.index[0]), f"round_id {rid!r} spans several companies")
        if g["round_type"].nunique() > 1:
            rep.warn(t, line_of(g.index[0]), f"round_id {rid!r}: sources disagree on round_type")
    firsts = df.drop_duplicates("round_id")
    for i in firsts[firsts.duplicated(subset=["company_id", "date", "round_type"], keep=False)].index:
        rep.warn(t, line_of(i), "two round_ids with the same company/date/round_type (same deal?)")


def rules_shipments(df: pd.DataFrame, rep: Report) -> None:
    for i, r in df.iterrows():
        if blank(r["units"]) and blank(r["units_text"]):
            rep.error("shipments", line_of(i), "`units` blank: put the source's wording in `units_text`")
        if r["source_type"] == "third_party" and blank(r["data_provider"]):
            rep.error("shipments", line_of(i), "third_party rows need `data_provider`")
        if RE_YEAR.match(r["year"]) and int(r["year"]) > TODAY.year:
            rep.error("shipments", line_of(i), "`year` is in the future (forecasts belong in forecasts.csv)")
        if r["period"] in schema.PERIODS_NEEDING_AS_OF and blank(r["as_of"]):
            rep.error("shipments", line_of(i), f"`period = {r['period']}` needs `as_of`")
    check_not_future("shipments", df, ["as_of"], rep)


def rules_valuations_revenue(df: pd.DataFrame, rep: Report) -> None:
    t = "valuations_revenue"
    for i, r in df.iterrows():
        if all(blank(r[c]) for c in ("valuation_usd", "revenue_usd", "net_income_usd")):
            rep.error(t, line_of(i), "row has no valuation, revenue or net income")
        if not blank(r["valuation_usd"]) and blank(r["valuation_type"]):
            rep.error(t, line_of(i), "`valuation_usd` needs `valuation_type`")
        has_financials = not (blank(r["revenue_usd"]) and blank(r["net_income_usd"]))
        if has_financials and blank(r["revenue_period"]):
            rep.error(t, line_of(i), "revenue / net income need `revenue_period`")
        if not blank(r["revenue_usd"]) and blank(r["revenue_scope"]):
            rep.error(t, line_of(i), "`revenue_usd` needs `revenue_scope`")
    check_not_future(t, df, ["date"], rep)


def rules_sector_funding(df: pd.DataFrame, rep: Report) -> None:
    t = "sector_funding"
    for i, r in df.iterrows():
        if not RE_YEAR.match(r["year"]):
            continue
        year = int(r["year"])
        if RE_DATE.match(r["period_end"]):
            if int(r["period_end"][:4]) != year:
                rep.error(t, line_of(i), "`period_end` outside `year`")
            if r["period_end"].endswith("-12-31"):
                rep.warn(t, line_of(i), "`period_end` is Dec 31: leave blank for full-year figures")
        elif year >= TODAY.year:
            rep.error(t, line_of(i), "current-year totals must set `period_end` (YTD)")


def rules_forecasts(df: pd.DataFrame, rep: Report) -> None:
    t = "forecasts"
    for i, r in df.iterrows():
        money = r["metric"] in schema.MONEY_FORECAST_METRICS
        if money and blank(r["value_usd"]):
            rep.error(t, line_of(i), f"`{r['metric']}` needs `value_usd`")
        if not money and blank(r["units"]):
            rep.error(t, line_of(i), f"`{r['metric']}` needs `units`")
        valid_years = RE_PDATE.match(r["publish_date"]) and RE_YEAR.match(r["target_year"])
        if valid_years and int(r["target_year"]) < int(r["publish_date"][:4]):
            rep.error(t, line_of(i), "`target_year` before `publish_date`")
    check_not_future(t, df, ["publish_date"], rep)


def rules_deployment_evidence(df: pd.DataFrame, rep: Report) -> None:
    t = "deployment_evidence"
    for i, r in df.iterrows():
        if blank(r["value"]) and blank(r["value_text"]):
            rep.error(t, line_of(i), "`value` blank: put the source's wording in `value_text`")
        if r["metric"] == "orders_value_usd" and r["unit"] != "USD":
            rep.error(t, line_of(i), "`orders_value_usd` rows must have `unit = USD`")
    check_not_future(t, df, ["as_of"], rep)


def printed_forms(value: float) -> list[str]:
    """Ways a filing prints a number: '1,131,860', '453', '252.5 million'."""
    forms = [f"{value:,.0f}", f"{value:.0f}"] if value == int(value) else [f"{value:,}"]
    if value >= 1e6:
        forms.append(f"{value / 1e6:g} million")
    return forms


def rules_company_financial_items(df: pd.DataFrame, rep: Report) -> None:
    t = "company_financial_items"
    for i, r in df.iterrows():
        if r["item"] in schema.TEXT_ITEMS:
            if not blank(r["value"]) or r["unit"] != "statement":
                rep.error(t, line_of(i), "quoted statements have a blank `value` and `unit = statement`")
            continue
        value = num(r["value"])
        if value is None:
            rep.error(t, line_of(i), f"`value` required for item {r['item']!r}")
        elif not any(form in r["quote_text"] for form in printed_forms(value)):
            rep.error(t, line_of(i), f"`value` {r['value']} is not printed in `quote_text`")
        if not r["page_or_section"].startswith(("p. ", "pp. ", "field ")):
            rep.error(t, line_of(i), "`page_or_section` must start with 'p. ', 'pp. ' or 'field ' (register data)")


TABLE_RULES: dict[str, Callable[[pd.DataFrame, Report], None]] = {
    "companies": rules_companies,
    "funding_rounds": rules_funding_rounds,
    "shipments": rules_shipments,
    "valuations_revenue": rules_valuations_revenue,
    "sector_funding": rules_sector_funding,
    "forecasts": rules_forecasts,
    "deployment_evidence": rules_deployment_evidence,
    "company_financial_items": rules_company_financial_items,
}


# --- Entry points ----------------------------------------------------------------


def validate_data(data_dir: Path = DATA) -> tuple[Report, dict[str, pd.DataFrame]]:
    """Run every data check on the CSVs in `data_dir`."""
    rep = Report()
    frames: dict[str, pd.DataFrame] = {}
    for table in schema.TABLES:
        df = load(data_dir, table, rep)
        if df is None:
            continue
        frames[table] = df
        check_cells(table, df, rep)
        check_duplicates(table, df, rep)
        check_qualifiers(table, df, rep)
        if "source_date" in df.columns:
            check_sources(table, df, rep)
        if table in TABLE_RULES:
            TABLE_RULES[table](df, rep)

    rates = {}
    if "fx_rates" in frames:
        rates = {
            (r["date"], r["currency"]): float(r["rate"])
            for _, r in frames["fx_rates"].iterrows()
            if RE_NUM.match(r["rate"])
        }
    for table in schema.FX_TRIPLES:
        if table in frames:
            check_fx(table, frames[table], rates, rep)
    if "companies" in frames:
        check_foreign_keys(frames, rep)
    return rep, frames


def check_repo(rep: Report, root: Path = ROOT) -> None:
    """Repo-wide policies that are not about a single table."""
    for folder in ("src", "charts", "datawrapper", "analysis", "tests"):
        for py in (root / folder).rglob("*.py"):
            if py == root / "src" / "style.py":
                continue
            for n, text in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if RE_HEX.search(text):
                    rep.error(str(py.relative_to(root)), n, "hex colour outside src/style.py")
    for csv in (root / "data").glob("*.csv"):
        if "caterpillar" in csv.read_text(encoding="utf-8").lower():
            rep.error(csv.name, None, "mentions Caterpillar: out of scope by policy")
    dd = root / "DATA_DICTIONARY.md"
    if not dd.exists() or dd.read_text(encoding="utf-8").replace("\r\n", "\n") != schema.render_markdown():
        rep.error("DATA_DICTIONARY.md", None, "stale: run `python -m src.schema`")


def summary(frames: dict[str, pd.DataFrame]) -> str:
    """Rows per file and share of each confidence grade."""

    def pct(counts: Counter, n: int) -> list[str]:
        return [f"{100 * counts[k] / n:.0f}%" if n else "-" for k in schema.CONFIDENCE]

    lines = [f"{'file':<30}{'rows':>6}{'V':>8}{'R':>8}{'U':>8}", "-" * 60]
    total: Counter = Counter()
    n_total = 0
    for table in schema.TABLES:
        df = frames.get(table)
        if df is None:
            lines.append(f"{table + '.csv':<30}{'-':>6}")
            continue
        cells = ["", "", ""]
        if "confidence" in df.columns:
            counts = Counter(df["confidence"])
            total.update(counts)
            n_total += len(df)
            cells = pct(counts, len(df))
        lines.append(f"{table + '.csv':<30}{len(df):>6}" + "".join(f"{c:>8}" for c in cells))
    lines += ["-" * 60, f"{'fact rows':<30}{n_total:>6}" + "".join(f"{c:>8}" for c in pct(total, n_total))]
    return "\n".join(lines)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rep, frames = validate_data()
    check_repo(rep)
    print(summary(frames))
    for w in rep.warnings:
        print(f"WARN  {w}")
    for e in rep.errors:
        print(f"ERROR {e}")
    print(f"\n{len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())

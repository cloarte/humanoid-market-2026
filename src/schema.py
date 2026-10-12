"""Single source of truth for every table: columns, types and controlled vocabularies.

`src/validate.py` enforces these rules. `python -m src.schema` regenerates
DATA_DICTIONARY.md, and validate.py fails if the committed dictionary is stale.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --- Controlled vocabularies -------------------------------------------------

CONFIDENCE = ("V", "R", "U")
QUALIFIERS = ("eq", "approx", "gt", "gte", "lt", "lte", "range")
SEGMENTS = ("humanoid_fullstack", "foundation_model", "data_infra", "component", "big_tech_program")
COMPANY_STATUS = ("private", "public", "acquired", "spac_pending")
ROUND_STATUS = ("closed", "announced", "in_talks", "term_sheet")
ROUND_TYPES = (
    "pre_seed",
    "seed",
    "series_a",
    "series_b",
    "series_c",
    "series_d",
    "series_e",
    "series_f",
    "extension",
    "strategic",
    "debt",
    "spac",
    "ipo",
    "majority_stake",
    "acquisition",
    "undisclosed",
)
SHIPMENT_METRICS = ("shipped", "deployed", "produced", "capacity", "preorders")
SHIPMENT_PERIODS = ("FY", "H1", "H2", "Q1", "Q2", "Q3", "Q4", "YTD", "cumulative")
SOURCE_TYPES = ("company", "third_party", "press_estimate")
VALUATION_TYPES = ("private_post_money", "ipo", "market_cap", "secondary")
REVENUE_SCOPES = ("total", "segment", "run_rate", "unspecified")
SECTOR_SCOPES = ("robotics_all", "humanoid")
FORECAST_METRICS = ("annual_revenue", "market_size", "annual_units", "installed_base", "total_economic_value")
MONEY_FORECAST_METRICS = ("annual_revenue", "market_size", "total_economic_value")  # need value_usd; others units
FORECAST_SCENARIOS = ("base", "low", "high", "bear", "bull", "blue_sky")
PERIODS_NEEDING_AS_OF = ("YTD", "cumulative")
PRICE_KINDS = (
    "list_price",
    "target_price",
    "price_estimate",
    "bom_estimate",
    "production_cost_estimate",
    "subscription_monthly",
)
PRODUCT_CLASSES = ("full_size", "compact", "generic")
DEPLOYMENT_STAGES = ("pilot", "commercial", "internal", "contracted")
EVIDENCE_METRICS = (
    "robots_deployed",
    "robots_doing_useful_work",
    "operating_hours",
    "output_supported",
    "items_handled",
    "orders_units",
    "orders_value_usd",
    "customer_agreement",  # a named purchase, order or agreement with no count
)
VERIFICATION_LEVELS = ("regulatory_filing", "customer_statement", "company_statement", "third_party_report")
FINANCIAL_ITEMS = (
    "net_sales_related_parties",
    "stock_compensation_expense",
    "stock_compensation_increase",
    "cash_and_equivalents",
    "deferred_revenue",
    "warrants_per_robot",
    "warrant_minimum_robots",
    "going_concern_auditor",
    "going_concern_company",
    "net_sales_to_customer",
    "statutory_revenue",
    "accounts_audited",
)
TEXT_ITEMS = ("going_concern_auditor", "going_concern_company", "accounts_audited")  # quoted statements, no number

# Pseudo company_ids for rows that describe a market aggregate or a generic product,
# not a single firm. They are valid foreign keys but never appear in companies.csv.
RESERVED_COMPANY_IDS = {
    "_all": "Global market aggregate (e.g. total humanoid shipments).",
    "_generic": "Generic humanoid of any origin (e.g. an analyst cost or price estimate).",
    "_generic_cn": "Generic Chinese-built humanoid (e.g. an analyst BOM estimate).",
    "_generic_west": "Generic Western-built humanoid (e.g. an analyst cost estimate).",
}


# --- Column specification ----------------------------------------------------


@dataclass(frozen=True)
class Col:
    name: str
    kind: str  # id | text | enum | iso2 | ccy | int | num | year | date | pdate | url
    desc: str
    required: bool = False
    enum: tuple[str, ...] = ()
    signed: bool = False  # numeric column that may be negative (e.g. net income)


KIND_DOC = {
    "id": "slug `[a-z0-9-]`",
    "text": "text",
    "enum": "enum",
    "iso2": "ISO 3166-1 alpha-2",
    "ccy": "ISO 4217",
    "int": "integer ≥ 0",
    "num": "number ≥ 0",
    "year": "year (YYYY)",
    "date": "date YYYY-MM-DD",
    "pdate": "date YYYY[-MM[-DD]]",
    "url": "URL (http/https)",
}

COMMON = [
    Col("source_url", "url", "Public page where the value in this row can be read.", required=True),
    Col("source_name", "text", "Publisher of that page (outlet, company, regulator).", required=True),
    Col("source_date", "date", "Publication date of the source page.", required=True),
    Col("accessed_date", "date", "Date we last opened the URL and confirmed the figure.", required=True),
    Col(
        "confidence",
        "enum",
        "`V` verified, `R` reported, `U` unverified/conflicting (see conventions).",
        required=True,
        enum=CONFIDENCE,
    ),
    Col("notes", "text", "Verbatim figure as printed, conversions, caveats, conflicts."),
]


def _q(target: str) -> Col:
    return Col(f"{target}_qualifier", "enum", f"How the source states `{target}`; blank means `eq`.", enum=QUALIFIERS)


TABLES: dict[str, dict] = {
    "companies": {
        "title": "Companies in scope (dimension table).",
        "key": ["company_id"],
        "cols": [
            Col("company_id", "id", "Primary key, lowercase hyphenated slug (e.g. `figure-ai`).", required=True),
            Col("name", "text", "Display name.", required=True),
            Col("country", "iso2", "Country of current headquarters.", required=True),
            Col("segment", "enum", "Primary business segment.", required=True, enum=SEGMENTS),
            Col("status", "enum", "Ownership status today.", required=True, enum=COMPANY_STATUS),
            Col("ticker", "text", "Exchange ticker if listed."),
            Col("exchange", "text", "Listing venue (e.g. `HKEX`, `SSE STAR`)."),
            *COMMON,
        ],
    },
    "funding_rounds": {
        "title": (
            "Deals (equity rounds, SPACs, stake sales). One row per (deal, source): `round_id` names the deal "
            "and is shared by every source row about it; each row holds only what its own source states. "
            "Valuations set by a round live here."
        ),
        "key": ["round_id", "source_url"],
        "cols": [
            Col(
                "round_id",
                "id",
                "Deal id `<company_id>-<yyyy-mm>-<round_type>`, shared by all source rows of a deal.",
                required=True,
            ),
            Col("company_id", "id", "Foreign key to companies.csv.", required=True),
            Col(
                "date",
                "pdate",
                "Announcement date (reduced precision allowed when only month/year is known).",
                required=True,
            ),
            Col("round_type", "enum", "Round label.", required=True, enum=ROUND_TYPES),
            Col("amount_local", "num", "Round size in the currency announced."),
            Col("currency", "ccy", "Currency of `amount_local`."),
            Col("amount_usd", "num", "Round size in USD (converted per METHODOLOGY if not USD)."),
            _q("amount"),
            Col(
                "post_money_usd",
                "num",
                "Valuation the source explicitly calls post-money (or says includes the new money), USD.",
            ),
            Col("pre_money_usd", "num", "Valuation the source explicitly calls pre-money, USD."),
            Col(
                "valuation_local",
                "num",
                "Valuation in the currency reported, when not USD (basis per the columns used).",
            ),
            Col("valuation_usd", "num", "Valuation when the source does not say pre- or post-money, USD."),
            _q("valuation"),
            Col("fx_rate", "num", "Local currency per 1 USD used for conversion."),
            Col("fx_date", "date", "Date of the `fx_rate` observation."),
            Col("lead_investors", "text", "Lead investors, `; `-separated."),
            Col("other_investors", "text", "Other named investors, `; `-separated."),
            Col("status", "enum", "Deal stage. `in_talks` rows can never be `V`.", required=True, enum=ROUND_STATUS),
            *COMMON,
        ],
    },
    "shipments": {
        "title": "Unit volumes, one row per (company, year, period, metric, source). Conflicts are kept.",
        "key": ["company_id", "year", "period", "metric", "source_type", "data_provider", "source_url"],
        "cols": [
            Col("company_id", "id", "Foreign key to companies.csv, or `_all` for the global total.", required=True),
            Col("year", "year", "Calendar year of the period.", required=True),
            Col("period", "enum", "Period within the year.", required=True, enum=SHIPMENT_PERIODS),
            Col("as_of", "pdate", "Date the figure refers to; required for `YTD` and `cumulative` periods."),
            Col("units", "int", "Unit count; blank when the source gives no number (see `units_text`)."),
            _q("units"),
            Col(
                "units_text", "text", "Figure exactly as worded, required when `units` is blank (e.g. `a few hundred`)."
            ),
            Col("metric", "enum", "What is being counted.", required=True, enum=SHIPMENT_METRICS),
            Col("source_type", "enum", "Who produced the number.", required=True, enum=SOURCE_TYPES),
            Col("data_provider", "text", "Originating analyst firm when `source_type = third_party` (e.g. `Omdia`)."),
            *COMMON,
        ],
    },
    "valuations_revenue": {
        "title": (
            "Valuations not set by a funding round (IPO price, market cap, secondary) plus revenue and "
            "net income. `date` is the valuation date, or the last day of `revenue_period` for financials."
        ),
        "key": ["company_id", "date", "valuation_type", "revenue_period", "revenue_scope", "source_url"],
        "cols": [
            Col("company_id", "id", "Foreign key to companies.csv.", required=True),
            Col("date", "pdate", "Date the valuation applies to (deal, listing or market-cap date).", required=True),
            Col("valuation_usd", "num", "Valuation in USD."),
            Col("valuation_local", "num", "Valuation in the currency reported, when not USD."),
            Col("valuation_currency", "ccy", "Currency of `valuation_local`."),
            Col("valuation_type", "enum", "Kind of valuation.", enum=VALUATION_TYPES),
            _q("valuation"),
            Col("revenue_local", "num", "Revenue in the reporting currency."),
            Col("revenue_currency", "ccy", "Currency of `revenue_local` and `net_income_local`."),
            Col("revenue_usd", "num", "Revenue in USD."),
            _q("revenue"),
            Col("revenue_period", "text", "Period covered, e.g. `FY2025`, `H1 2026`."),
            Col(
                "revenue_scope",
                "enum",
                "`total`, a reported `segment`, a `run_rate`, or `unspecified` wording.",
                enum=REVENUE_SCOPES,
            ),
            Col("net_income_local", "num", "Net income in the reporting currency (negative = loss).", signed=True),
            Col("net_income_usd", "num", "Net income in USD (negative = loss).", signed=True),
            Col("fx_rate", "num", "Local currency per 1 USD used for every local amount in the row."),
            Col("fx_date", "date", "Date of the `fx_rate` observation."),
            Col(
                "calculation",
                "text",
                "For derived values: the formula and the source of each input (e.g. closing price times shares). "
                "Blank when `source_url` states the figure itself.",
            ),
            *COMMON,
        ],
    },
    "sector_funding": {
        "title": "Sector-level venture totals by year as published by a data provider.",
        "key": ["year", "scope", "data_provider", "period_end", "source_url"],
        "cols": [
            Col("year", "year", "Calendar year.", required=True),
            Col("scope", "enum", "Which universe the total covers.", required=True, enum=SECTOR_SCOPES),
            Col("amount_usd", "num", "Total venture funding, USD.", required=True),
            _q("amount"),
            Col("deal_count", "int", "Number of deals, if published."),
            Col("period_end", "date", "Last day covered when the figure is year-to-date; blank = full year."),
            Col("data_provider", "text", "Database behind the figure (e.g. `Crunchbase`, `PitchBook`).", required=True),
            Col("definition_note", "text", "Provider's definition of the scope, as stated."),
            *COMMON,
        ],
    },
    "forecasts": {
        "title": "Published market forecasts, one row per (publisher, date, target year, metric, scenario).",
        "key": ["publisher", "publish_date", "target_year", "metric", "scenario", "source_url"],
        "cols": [
            Col("publisher", "text", "Institution that made the forecast.", required=True),
            Col("publish_date", "pdate", "Date the forecast was published.", required=True),
            Col("target_year", "year", "Year the forecast refers to.", required=True),
            Col(
                "metric",
                "enum",
                "What is forecast. `annual_revenue` only when the publisher says annual revenue; `market_size` for "
                "'market' or 'TAM' figures whose basis is not stated.",
                required=True,
                enum=FORECAST_METRICS,
            ),
            Col(
                "scenario",
                "enum",
                "Scenario label if the publisher gives several; blank if single.",
                enum=FORECAST_SCENARIOS,
            ),
            Col("value_usd", "num", "Forecast value in USD (monetary metrics)."),
            _q("value"),
            Col("units", "num", "Forecast units (unit metrics)."),
            _q("units"),
            Col("scope_definition", "text", "What the number includes, in the publisher's terms.", required=True),
            *COMMON,
        ],
    },
    "prices_bom": {
        "title": "List prices, target prices and cost/BOM estimates.",
        "key": ["company_id", "product", "year", "kind", "source_url"],
        "cols": [
            Col("company_id", "id", "Foreign key to companies.csv, or `_generic_cn` / `_generic_west`.", required=True),
            Col("product", "text", "Product or estimate label.", required=True),
            Col(
                "product_class",
                "enum",
                "`full_size` (adult-height humanoid), `compact` (smaller models), `generic` (analyst estimate).",
                required=True,
                enum=PRODUCT_CLASSES,
            ),
            Col(
                "year",
                "year",
                "Year the price was quoted (list and target prices) or the year an estimate refers to.",
                required=True,
            ),
            Col("value_usd", "num", "Value in USD (low end when `value_qualifier = range`).", required=True),
            Col("value_usd_high", "num", "High end of a range; only with `value_qualifier = range`."),
            _q("value"),
            Col("value_local", "num", "Value in the currency quoted, when not USD."),
            Col("currency", "ccy", "Currency of `value_local`."),
            Col("fx_rate", "num", "Local currency per 1 USD."),
            Col("fx_date", "date", "Date of the `fx_rate` observation."),
            Col("kind", "enum", "What the number is.", required=True, enum=PRICE_KINDS),
            *COMMON,
        ],
    },
    "deployment_evidence": {
        "title": (
            "Evidence that robots do useful work for someone: one row per claim (company, customer, metric, date, "
            "source). `verification` records who stands behind the number; negative evidence is kept too."
        ),
        "key": ["company_id", "customer", "metric", "as_of", "source_url"],
        "cols": [
            Col("company_id", "id", "Foreign key to companies.csv.", required=True),
            Col("customer", "text", "Customer or site as named by the source; blank if undisclosed."),
            Col("site_country", "iso2", "Country of the site, when stated."),
            Col(
                "stage",
                "enum",
                "`pilot`, paid `commercial` use, `internal` use, or `contracted` (ordered, not delivered).",
                required=True,
                enum=DEPLOYMENT_STAGES,
            ),
            Col("task", "text", "What the robots do, in the source's terms."),
            Col("metric", "enum", "What is counted.", required=True, enum=EVIDENCE_METRICS),
            Col("value", "num", "The number; blank when the source gives only words (see `value_text`)."),
            Col("value_qualifier", "enum", "How the source states `value`; blank means `eq`.", enum=QUALIFIERS),
            Col("value_text", "text", "Figure exactly as worded, required when `value` is blank."),
            Col("unit", "text", "Unit of `value` (e.g. `hours`, `robots`, `BMW X3 vehicles`, `USD`).", required=True),
            Col("as_of", "pdate", "Date or period the figure refers to.", required=True),
            Col("verification", "enum", "Who stands behind the figure.", required=True, enum=VERIFICATION_LEVELS),
            *COMMON,
        ],
    },
    "company_financial_items": {
        "title": (
            "Single line items and statements from a company's filings that other tables do not hold (e.g. sales to "
            "related parties, stock compensation, cash, going-concern language). One row per item, with the text "
            "quoted verbatim and the page where it is printed."
        ),
        "key": ["item_id"],
        "cols": [
            Col(
                "item_id", "id", "Primary key, e.g. `agility-robotics-fy2025-net-sales-related-parties`.", required=True
            ),
            Col("company_id", "id", "Foreign key to companies.csv.", required=True),
            Col(
                "period",
                "text",
                "Period or date the item refers to (`FY2025`, `H1 2026`, `2026-06-30`).",
                required=True,
            ),
            Col("item", "enum", "What the row records.", required=True, enum=FINANCIAL_ITEMS),
            Col("counterparty", "text", "Customer or related party the item concerns, when it names one."),
            Col("value", "num", "The number; blank only for quoted statements (going-concern, audit status)."),
            Col("value_qualifier", "enum", "How the source states `value`; blank means `eq`.", enum=QUALIFIERS),
            Col(
                "unit",
                "text",
                "Unit of `value` (`USD`, `RMB thousand`, `RMB 10 thousand`, `NOK`, `warrants per robot`, `robots`, "
                "`statement`).",
                required=True,
            ),
            Col("quote_text", "text", "Text exactly as printed in the source, including the figure.", required=True),
            Col(
                "page_or_section",
                "text",
                "Page number and section of the source (e.g. `p. F-47, Statements of Operations`).",
                required=True,
            ),
            *COMMON,
        ],
    },
    "fx_rates": {
        "title": "Reference FX observations used by every conversion (written by `python -m src.fx --fetch`).",
        "key": ["date", "currency"],
        "cols": [
            Col("date", "date", "Observation date.", required=True),
            Col("currency", "ccy", "Currency quoted against USD.", required=True),
            Col("rate", "num", "Units of `currency` per 1 USD.", required=True),
            Col("series_id", "text", "Provider series id (e.g. FRED `DEXCHUS`).", required=True),
            Col("source_url", "url", "Series page.", required=True),
            Col("source_name", "text", "Provider.", required=True),
        ],
    },
}

# For each table: (local amount column, currency column, USD column) triples that must be FX-consistent.
FX_TRIPLES = {
    "funding_rounds": [("amount_local", "currency", "amount_usd"), ("valuation_local", "currency", "valuation_usd")],
    "valuations_revenue": [
        ("valuation_local", "valuation_currency", "valuation_usd"),
        ("revenue_local", "revenue_currency", "revenue_usd"),
        ("net_income_local", "revenue_currency", "net_income_usd"),
    ],
    "prices_bom": [("value_local", "currency", "value_usd")],
}

# Qualifier column -> the value column(s) it describes, and the optional high-end column for ranges.
QUALIFIER_TARGETS = {
    "funding_rounds": {
        "amount_qualifier": (["amount_usd", "amount_local"], None),
        "valuation_qualifier": (["post_money_usd", "pre_money_usd", "valuation_usd", "valuation_local"], None),
    },
    "shipments": {"units_qualifier": (["units"], None)},
    "valuations_revenue": {
        "valuation_qualifier": (["valuation_usd", "valuation_local"], None),
        "revenue_qualifier": (["revenue_usd", "revenue_local"], None),
    },
    "sector_funding": {"amount_qualifier": (["amount_usd"], None)},
    "forecasts": {"value_qualifier": (["value_usd"], None), "units_qualifier": (["units"], None)},
    "prices_bom": {"value_qualifier": (["value_usd"], "value_usd_high")},
    "deployment_evidence": {"value_qualifier": (["value"], None)},
    "company_financial_items": {"value_qualifier": (["value"], None)},
}


def columns(table: str) -> list[str]:
    return [c.name for c in TABLES[table]["cols"]]


# --- DATA_DICTIONARY.md generator --------------------------------------------

CONVENTIONS = """\
# Data dictionary

> Generated from `src/schema.py` by `python -m src.schema`. Do not edit by hand;
> `src/validate.py` fails if this file is out of date.

## Conventions

- **Files.** UTF-8 CSV with a header row, one file per table in `data/`.
- **Missing values.** An empty cell means *not disclosed / not found*, never zero.
  Every gap that matters is logged in `GAPS.md`.
- **Numbers.** Plain digits, no thousands separators, no units in the cell, full
  amounts (`39000000000`, not `39` or `39B`). Only net income may be negative.
- **Dates.** `date` columns are full ISO dates (`YYYY-MM-DD`). `pdate` columns allow
  ISO reduced precision (`YYYY` or `YYYY-MM`) when the source gives no day; we never
  invent the missing part.
- **Qualifiers.** Sources often say "more than", "about" or "under". The value cell
  holds the number as printed and the `*_qualifier` column records how it was stated:
  `eq` exact (default when blank), `approx` (~), `gt` (>), `gte` (at least), `lt` (<),
  `lte` (up to), `range` (low in the value column, high in `*_high`). Charts print the
  matching symbol (e.g. `>$1B`, `~5,500 units`).
- **FX.** `fx_rate` is units of local currency per 1 USD; `usd = local / fx_rate`.
  Every rate used must exist in `data/fx_rates.csv`. See METHODOLOGY.md.
- **Lists.** Multi-valued text cells are separated by `; `.
- **Reserved ids.** `company_id` may take these values, which are not companies:
{reserved}
- **Confidence.**
  - `V` verified: primary source (company, regulator, exchange filing) or a major
    outlet reporting the figure as fact.
  - `R` reported: unnamed sources, "in talks", or a secondary aggregator only.
  - `U` unverified / conflicting: sources disagree or the figure could not be confirmed.
"""


SCORECARD_DOC = """\
## Derived: `outputs/disclosure_scorecard.csv`

What each humanoid maker publicly discloses about useful work (`python -m analysis.disclosure_scorecard`).
An evidence audit, not a ranking of quality. One row per company and item: `status`, `evidence_rows`
(`file.csv:line` in `data/`), `source_url` and `note`. Statuses:

- `✓` disclosed: the company itself, its filing, or a named customer states the item.
- `◐` partial: stated only in part: as a bound ("more than"), self-reported without verification, for a
  pilot rather than paid use, or reported by the press rather than the company or the customer.
- `✗` not found: not found in the public sources reviewed as of the data cut-off (what was searched is
  in GAPS.md).

Third-party estimates (e.g. Omdia's unit counts) never count as a company disclosure.

"""


SCORECARD_ITEMS = [
    (
        "units",
        "Units",
        "the company states how many robots it shipped or sold in a full year",
        'Unitree 5,511 ✓; AgiBot "more than 5,100" cumulative ◐; preorders or capacity ✗',
    ),
    (
        "revenue",
        "Revenue",
        "the company states, or audited accounts give, its annual revenue",
        "1X: a Norwegian subsidiary's statutory accounts only ◐",
    ),
    (
        "paid_deployment",
        "At work",
        "the company states how many robots work for paying customers, excluding pilots",
        'AgiBot "more than 300" at one park, counted by the press ◐; Agility gives hours but no count ✗',
    ),
    (
        "hours",
        "Hours",
        "the company or a filing reports operating hours at paying customers",
        "Agility 65,000+ hours ✓; Figure's BMW pilot hours via a secondary report ◐",
    ),
    (
        "customer",
        "Customer",
        "a purchase, order or commercial agreement with a named customer, stated by the company, the customer "
        "or a filing (pilots included)",
        "Figure–BMW ✓ (pilot); Unitree's sales to Galbot in its prospectus ✓; a press report only ◐",
    ),
    (
        "related_parties",
        "Rel. party",
        "the share or amount of sales to related parties is disclosed",
        "Agility 63.5% ✓",
    ),
    (
        "audited",
        "Audited",
        "the company is listed or files audited statements (e.g. with the SEC)",
        "Tesla ◐: group accounts audited, Optimus not reported separately",
    ),
]


def render_markdown() -> str:
    reserved = "\n".join(f"  - `{k}`: {v}" for k, v in RESERVED_COMPANY_IDS.items())
    out = [CONVENTIONS.format(reserved=reserved)]
    for table, spec in TABLES.items():
        out.append(f"## `data/{table}.csv`\n")
        out.append(spec["title"] + "\n")
        out.append(f"Uniqueness key: `{'`, `'.join(spec['key'])}`.\n")
        out.append("| column | type | req. | allowed values | description |")
        out.append("|---|---|---|---|---|")
        for c in spec["cols"]:
            kind = "number (may be < 0)" if c.signed else KIND_DOC[c.kind]
            allowed = ", ".join(f"`{v}`" for v in c.enum)
            out.append(f"| `{c.name}` | {kind} | {'yes' if c.required else ''} | {allowed} | {c.desc} |")
        out.append("")
    out.append(SCORECARD_DOC)
    out.append("| item | header | ✓ when | examples |")
    out.append("|---|---|---|---|")
    out += [f"| `{item}` | {header} | {when} | {examples} |" for item, header, when, examples in SCORECARD_ITEMS]
    out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    path = ROOT / "DATA_DICTIONARY.md"
    path.write_text(render_markdown(), encoding="utf-8", newline="\n")
    print(f"wrote {path.relative_to(ROOT)}", file=sys.stderr)

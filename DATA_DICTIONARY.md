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
  - `_all`: Global market aggregate (e.g. total humanoid shipments).
  - `_generic`: Generic humanoid of any origin (e.g. an analyst cost or price estimate).
  - `_generic_cn`: Generic Chinese-built humanoid (e.g. an analyst BOM estimate).
  - `_generic_west`: Generic Western-built humanoid (e.g. an analyst cost estimate).
- **Confidence.**
  - `V` verified: primary source (company, regulator, exchange filing) or a major
    outlet reporting the figure as fact.
  - `R` reported: unnamed sources, "in talks", or a secondary aggregator only.
  - `U` unverified / conflicting: sources disagree or the figure could not be confirmed.

## `data/companies.csv`

Companies in scope (dimension table).

Uniqueness key: `company_id`.

| column | type | req. | allowed values | description |
|---|---|---|---|---|
| `company_id` | slug `[a-z0-9-]` | yes |  | Primary key, lowercase hyphenated slug (e.g. `figure-ai`). |
| `name` | text | yes |  | Display name. |
| `country` | ISO 3166-1 alpha-2 | yes |  | Country of current headquarters. |
| `segment` | enum | yes | `humanoid_fullstack`, `foundation_model`, `data_infra`, `component`, `big_tech_program` | Primary business segment. |
| `status` | enum | yes | `private`, `public`, `acquired`, `spac_pending` | Ownership status today. |
| `ticker` | text |  |  | Exchange ticker if listed. |
| `exchange` | text |  |  | Listing venue (e.g. `HKEX`, `SSE STAR`). |
| `source_url` | URL (http/https) | yes |  | Public page where the value in this row can be read. |
| `source_name` | text | yes |  | Publisher of that page (outlet, company, regulator). |
| `source_date` | date YYYY-MM-DD | yes |  | Publication date of the source page. |
| `accessed_date` | date YYYY-MM-DD | yes |  | Date we last opened the URL and confirmed the figure. |
| `confidence` | enum | yes | `V`, `R`, `U` | `V` verified, `R` reported, `U` unverified/conflicting (see conventions). |
| `notes` | text |  |  | Verbatim figure as printed, conversions, caveats, conflicts. |

## `data/funding_rounds.csv`

Deals (equity rounds, SPACs, stake sales). One row per (deal, source): `round_id` names the deal and is shared by every source row about it; each row holds only what its own source states. Valuations set by a round live here.

Uniqueness key: `round_id`, `source_url`.

| column | type | req. | allowed values | description |
|---|---|---|---|---|
| `round_id` | slug `[a-z0-9-]` | yes |  | Deal id `<company_id>-<yyyy-mm>-<round_type>`, shared by all source rows of a deal. |
| `company_id` | slug `[a-z0-9-]` | yes |  | Foreign key to companies.csv. |
| `date` | date YYYY[-MM[-DD]] | yes |  | Announcement date (reduced precision allowed when only month/year is known). |
| `round_type` | enum | yes | `pre_seed`, `seed`, `series_a`, `series_b`, `series_c`, `series_d`, `series_e`, `series_f`, `extension`, `strategic`, `debt`, `spac`, `ipo`, `majority_stake`, `acquisition`, `undisclosed` | Round label. |
| `amount_local` | number ≥ 0 |  |  | Round size in the currency announced. |
| `currency` | ISO 4217 |  |  | Currency of `amount_local`. |
| `amount_usd` | number ≥ 0 |  |  | Round size in USD (converted per METHODOLOGY if not USD). |
| `amount_qualifier` | enum |  | `eq`, `approx`, `gt`, `gte`, `lt`, `lte`, `range` | How the source states `amount`; blank means `eq`. |
| `post_money_usd` | number ≥ 0 |  |  | Valuation the source explicitly calls post-money (or says includes the new money), USD. |
| `pre_money_usd` | number ≥ 0 |  |  | Valuation the source explicitly calls pre-money, USD. |
| `valuation_local` | number ≥ 0 |  |  | Valuation in the currency reported, when not USD (basis per the columns used). |
| `valuation_usd` | number ≥ 0 |  |  | Valuation when the source does not say pre- or post-money, USD. |
| `valuation_qualifier` | enum |  | `eq`, `approx`, `gt`, `gte`, `lt`, `lte`, `range` | How the source states `valuation`; blank means `eq`. |
| `fx_rate` | number ≥ 0 |  |  | Local currency per 1 USD used for conversion. |
| `fx_date` | date YYYY-MM-DD |  |  | Date of the `fx_rate` observation. |
| `lead_investors` | text |  |  | Lead investors, `; `-separated. |
| `other_investors` | text |  |  | Other named investors, `; `-separated. |
| `status` | enum | yes | `closed`, `announced`, `in_talks`, `term_sheet` | Deal stage. `in_talks` rows can never be `V`. |
| `source_url` | URL (http/https) | yes |  | Public page where the value in this row can be read. |
| `source_name` | text | yes |  | Publisher of that page (outlet, company, regulator). |
| `source_date` | date YYYY-MM-DD | yes |  | Publication date of the source page. |
| `accessed_date` | date YYYY-MM-DD | yes |  | Date we last opened the URL and confirmed the figure. |
| `confidence` | enum | yes | `V`, `R`, `U` | `V` verified, `R` reported, `U` unverified/conflicting (see conventions). |
| `notes` | text |  |  | Verbatim figure as printed, conversions, caveats, conflicts. |

## `data/shipments.csv`

Unit volumes, one row per (company, year, period, metric, source). Conflicts are kept.

Uniqueness key: `company_id`, `year`, `period`, `metric`, `source_type`, `data_provider`, `source_url`.

| column | type | req. | allowed values | description |
|---|---|---|---|---|
| `company_id` | slug `[a-z0-9-]` | yes |  | Foreign key to companies.csv, or `_all` for the global total. |
| `year` | year (YYYY) | yes |  | Calendar year of the period. |
| `period` | enum | yes | `FY`, `H1`, `H2`, `Q1`, `Q2`, `Q3`, `Q4`, `YTD`, `cumulative` | Period within the year. |
| `as_of` | date YYYY[-MM[-DD]] |  |  | Date the figure refers to; required for `YTD` and `cumulative` periods. |
| `units` | integer ≥ 0 |  |  | Unit count; blank when the source gives no number (see `units_text`). |
| `units_qualifier` | enum |  | `eq`, `approx`, `gt`, `gte`, `lt`, `lte`, `range` | How the source states `units`; blank means `eq`. |
| `units_text` | text |  |  | Figure exactly as worded, required when `units` is blank (e.g. `a few hundred`). |
| `metric` | enum | yes | `shipped`, `deployed`, `produced`, `capacity`, `preorders` | What is being counted. |
| `source_type` | enum | yes | `company`, `third_party`, `press_estimate` | Who produced the number. |
| `data_provider` | text |  |  | Originating analyst firm when `source_type = third_party` (e.g. `Omdia`). |
| `source_url` | URL (http/https) | yes |  | Public page where the value in this row can be read. |
| `source_name` | text | yes |  | Publisher of that page (outlet, company, regulator). |
| `source_date` | date YYYY-MM-DD | yes |  | Publication date of the source page. |
| `accessed_date` | date YYYY-MM-DD | yes |  | Date we last opened the URL and confirmed the figure. |
| `confidence` | enum | yes | `V`, `R`, `U` | `V` verified, `R` reported, `U` unverified/conflicting (see conventions). |
| `notes` | text |  |  | Verbatim figure as printed, conversions, caveats, conflicts. |

## `data/valuations_revenue.csv`

Valuations not set by a funding round (IPO price, market cap, secondary) plus revenue and net income. `date` is the valuation date, or the last day of `revenue_period` for financials.

Uniqueness key: `company_id`, `date`, `valuation_type`, `revenue_period`, `revenue_scope`, `source_url`.

| column | type | req. | allowed values | description |
|---|---|---|---|---|
| `company_id` | slug `[a-z0-9-]` | yes |  | Foreign key to companies.csv. |
| `date` | date YYYY[-MM[-DD]] | yes |  | Date the valuation applies to (deal, listing or market-cap date). |
| `valuation_usd` | number ≥ 0 |  |  | Valuation in USD. |
| `valuation_local` | number ≥ 0 |  |  | Valuation in the currency reported, when not USD. |
| `valuation_currency` | ISO 4217 |  |  | Currency of `valuation_local`. |
| `valuation_type` | enum |  | `private_post_money`, `ipo`, `market_cap`, `secondary` | Kind of valuation. |
| `valuation_qualifier` | enum |  | `eq`, `approx`, `gt`, `gte`, `lt`, `lte`, `range` | How the source states `valuation`; blank means `eq`. |
| `revenue_local` | number ≥ 0 |  |  | Revenue in the reporting currency. |
| `revenue_currency` | ISO 4217 |  |  | Currency of `revenue_local` and `net_income_local`. |
| `revenue_usd` | number ≥ 0 |  |  | Revenue in USD. |
| `revenue_qualifier` | enum |  | `eq`, `approx`, `gt`, `gte`, `lt`, `lte`, `range` | How the source states `revenue`; blank means `eq`. |
| `revenue_period` | text |  |  | Period covered, e.g. `FY2025`, `H1 2026`. |
| `revenue_scope` | enum |  | `total`, `segment`, `run_rate`, `unspecified` | `total`, a reported `segment`, a `run_rate`, or `unspecified` wording. |
| `net_income_local` | number (may be < 0) |  |  | Net income in the reporting currency (negative = loss). |
| `net_income_usd` | number (may be < 0) |  |  | Net income in USD (negative = loss). |
| `fx_rate` | number ≥ 0 |  |  | Local currency per 1 USD used for every local amount in the row. |
| `fx_date` | date YYYY-MM-DD |  |  | Date of the `fx_rate` observation. |
| `calculation` | text |  |  | For derived values: the formula and the source of each input (e.g. closing price times shares). Blank when `source_url` states the figure itself. |
| `source_url` | URL (http/https) | yes |  | Public page where the value in this row can be read. |
| `source_name` | text | yes |  | Publisher of that page (outlet, company, regulator). |
| `source_date` | date YYYY-MM-DD | yes |  | Publication date of the source page. |
| `accessed_date` | date YYYY-MM-DD | yes |  | Date we last opened the URL and confirmed the figure. |
| `confidence` | enum | yes | `V`, `R`, `U` | `V` verified, `R` reported, `U` unverified/conflicting (see conventions). |
| `notes` | text |  |  | Verbatim figure as printed, conversions, caveats, conflicts. |

## `data/sector_funding.csv`

Sector-level venture totals by year as published by a data provider.

Uniqueness key: `year`, `scope`, `data_provider`, `period_end`, `source_url`.

| column | type | req. | allowed values | description |
|---|---|---|---|---|
| `year` | year (YYYY) | yes |  | Calendar year. |
| `scope` | enum | yes | `robotics_all`, `humanoid` | Which universe the total covers. |
| `amount_usd` | number ≥ 0 | yes |  | Total venture funding, USD. |
| `amount_qualifier` | enum |  | `eq`, `approx`, `gt`, `gte`, `lt`, `lte`, `range` | How the source states `amount`; blank means `eq`. |
| `deal_count` | integer ≥ 0 |  |  | Number of deals, if published. |
| `period_end` | date YYYY-MM-DD |  |  | Last day covered when the figure is year-to-date; blank = full year. |
| `data_provider` | text | yes |  | Database behind the figure (e.g. `Crunchbase`, `PitchBook`). |
| `definition_note` | text |  |  | Provider's definition of the scope, as stated. |
| `source_url` | URL (http/https) | yes |  | Public page where the value in this row can be read. |
| `source_name` | text | yes |  | Publisher of that page (outlet, company, regulator). |
| `source_date` | date YYYY-MM-DD | yes |  | Publication date of the source page. |
| `accessed_date` | date YYYY-MM-DD | yes |  | Date we last opened the URL and confirmed the figure. |
| `confidence` | enum | yes | `V`, `R`, `U` | `V` verified, `R` reported, `U` unverified/conflicting (see conventions). |
| `notes` | text |  |  | Verbatim figure as printed, conversions, caveats, conflicts. |

## `data/forecasts.csv`

Published market forecasts, one row per (publisher, date, target year, metric, scenario).

Uniqueness key: `publisher`, `publish_date`, `target_year`, `metric`, `scenario`, `source_url`.

| column | type | req. | allowed values | description |
|---|---|---|---|---|
| `publisher` | text | yes |  | Institution that made the forecast. |
| `publish_date` | date YYYY[-MM[-DD]] | yes |  | Date the forecast was published. |
| `target_year` | year (YYYY) | yes |  | Year the forecast refers to. |
| `metric` | enum | yes | `annual_revenue`, `market_size`, `annual_units`, `installed_base`, `total_economic_value` | What is forecast. `annual_revenue` only when the publisher says annual revenue; `market_size` for 'market' or 'TAM' figures whose basis is not stated. |
| `scenario` | enum |  | `base`, `low`, `high`, `bear`, `bull`, `blue_sky` | Scenario label if the publisher gives several; blank if single. |
| `value_usd` | number ≥ 0 |  |  | Forecast value in USD (monetary metrics). |
| `value_qualifier` | enum |  | `eq`, `approx`, `gt`, `gte`, `lt`, `lte`, `range` | How the source states `value`; blank means `eq`. |
| `units` | number ≥ 0 |  |  | Forecast units (unit metrics). |
| `units_qualifier` | enum |  | `eq`, `approx`, `gt`, `gte`, `lt`, `lte`, `range` | How the source states `units`; blank means `eq`. |
| `scope_definition` | text | yes |  | What the number includes, in the publisher's terms. |
| `source_url` | URL (http/https) | yes |  | Public page where the value in this row can be read. |
| `source_name` | text | yes |  | Publisher of that page (outlet, company, regulator). |
| `source_date` | date YYYY-MM-DD | yes |  | Publication date of the source page. |
| `accessed_date` | date YYYY-MM-DD | yes |  | Date we last opened the URL and confirmed the figure. |
| `confidence` | enum | yes | `V`, `R`, `U` | `V` verified, `R` reported, `U` unverified/conflicting (see conventions). |
| `notes` | text |  |  | Verbatim figure as printed, conversions, caveats, conflicts. |

## `data/prices_bom.csv`

List prices, target prices and cost/BOM estimates.

Uniqueness key: `company_id`, `product`, `year`, `kind`, `source_url`.

| column | type | req. | allowed values | description |
|---|---|---|---|---|
| `company_id` | slug `[a-z0-9-]` | yes |  | Foreign key to companies.csv, or `_generic_cn` / `_generic_west`. |
| `product` | text | yes |  | Product or estimate label. |
| `product_class` | enum | yes | `full_size`, `compact`, `generic` | `full_size` (adult-height humanoid), `compact` (smaller models), `generic` (analyst estimate). |
| `year` | year (YYYY) | yes |  | Year the price was quoted (list and target prices) or the year an estimate refers to. |
| `value_usd` | number ≥ 0 | yes |  | Value in USD (low end when `value_qualifier = range`). |
| `value_usd_high` | number ≥ 0 |  |  | High end of a range; only with `value_qualifier = range`. |
| `value_qualifier` | enum |  | `eq`, `approx`, `gt`, `gte`, `lt`, `lte`, `range` | How the source states `value`; blank means `eq`. |
| `value_local` | number ≥ 0 |  |  | Value in the currency quoted, when not USD. |
| `currency` | ISO 4217 |  |  | Currency of `value_local`. |
| `fx_rate` | number ≥ 0 |  |  | Local currency per 1 USD. |
| `fx_date` | date YYYY-MM-DD |  |  | Date of the `fx_rate` observation. |
| `kind` | enum | yes | `list_price`, `target_price`, `price_estimate`, `bom_estimate`, `production_cost_estimate`, `subscription_monthly` | What the number is. |
| `source_url` | URL (http/https) | yes |  | Public page where the value in this row can be read. |
| `source_name` | text | yes |  | Publisher of that page (outlet, company, regulator). |
| `source_date` | date YYYY-MM-DD | yes |  | Publication date of the source page. |
| `accessed_date` | date YYYY-MM-DD | yes |  | Date we last opened the URL and confirmed the figure. |
| `confidence` | enum | yes | `V`, `R`, `U` | `V` verified, `R` reported, `U` unverified/conflicting (see conventions). |
| `notes` | text |  |  | Verbatim figure as printed, conversions, caveats, conflicts. |

## `data/deployment_evidence.csv`

Evidence that robots do useful work for someone: one row per claim (company, customer, metric, date, source). `verification` records who stands behind the number; negative evidence is kept too.

Uniqueness key: `company_id`, `customer`, `metric`, `as_of`, `source_url`.

| column | type | req. | allowed values | description |
|---|---|---|---|---|
| `company_id` | slug `[a-z0-9-]` | yes |  | Foreign key to companies.csv. |
| `customer` | text |  |  | Customer or site as named by the source; blank if undisclosed. |
| `site_country` | ISO 3166-1 alpha-2 |  |  | Country of the site, when stated. |
| `stage` | enum | yes | `pilot`, `commercial`, `internal`, `contracted` | `pilot`, paid `commercial` use, `internal` use, or `contracted` (ordered, not delivered). |
| `task` | text |  |  | What the robots do, in the source's terms. |
| `metric` | enum | yes | `robots_deployed`, `robots_doing_useful_work`, `operating_hours`, `output_supported`, `items_handled`, `orders_units`, `orders_value_usd`, `customer_agreement` | What is counted. |
| `value` | number ≥ 0 |  |  | The number; blank when the source gives only words (see `value_text`). |
| `value_qualifier` | enum |  | `eq`, `approx`, `gt`, `gte`, `lt`, `lte`, `range` | How the source states `value`; blank means `eq`. |
| `value_text` | text |  |  | Figure exactly as worded, required when `value` is blank. |
| `unit` | text | yes |  | Unit of `value` (e.g. `hours`, `robots`, `BMW X3 vehicles`, `USD`). |
| `as_of` | date YYYY[-MM[-DD]] | yes |  | Date or period the figure refers to. |
| `verification` | enum | yes | `regulatory_filing`, `customer_statement`, `company_statement`, `third_party_report` | Who stands behind the figure. |
| `source_url` | URL (http/https) | yes |  | Public page where the value in this row can be read. |
| `source_name` | text | yes |  | Publisher of that page (outlet, company, regulator). |
| `source_date` | date YYYY-MM-DD | yes |  | Publication date of the source page. |
| `accessed_date` | date YYYY-MM-DD | yes |  | Date we last opened the URL and confirmed the figure. |
| `confidence` | enum | yes | `V`, `R`, `U` | `V` verified, `R` reported, `U` unverified/conflicting (see conventions). |
| `notes` | text |  |  | Verbatim figure as printed, conversions, caveats, conflicts. |

## `data/company_financial_items.csv`

Single line items and statements from a company's filings that other tables do not hold (e.g. sales to related parties, stock compensation, cash, going-concern language). One row per item, with the text quoted verbatim and the page where it is printed.

Uniqueness key: `item_id`.

| column | type | req. | allowed values | description |
|---|---|---|---|---|
| `item_id` | slug `[a-z0-9-]` | yes |  | Primary key, e.g. `agility-robotics-fy2025-net-sales-related-parties`. |
| `company_id` | slug `[a-z0-9-]` | yes |  | Foreign key to companies.csv. |
| `period` | text | yes |  | Period or date the item refers to (`FY2025`, `H1 2026`, `2026-06-30`). |
| `item` | enum | yes | `net_sales_related_parties`, `stock_compensation_expense`, `stock_compensation_increase`, `cash_and_equivalents`, `deferred_revenue`, `warrants_per_robot`, `warrant_minimum_robots`, `going_concern_auditor`, `going_concern_company`, `net_sales_to_customer`, `statutory_revenue`, `accounts_audited` | What the row records. |
| `counterparty` | text |  |  | Customer or related party the item concerns, when it names one. |
| `value` | number ≥ 0 |  |  | The number; blank only for quoted statements (going-concern, audit status). |
| `value_qualifier` | enum |  | `eq`, `approx`, `gt`, `gte`, `lt`, `lte`, `range` | How the source states `value`; blank means `eq`. |
| `unit` | text | yes |  | Unit of `value` (`USD`, `RMB thousand`, `RMB 10 thousand`, `NOK`, `warrants per robot`, `robots`, `statement`). |
| `quote_text` | text | yes |  | Text exactly as printed in the source, including the figure. |
| `page_or_section` | text | yes |  | Page number and section of the source (e.g. `p. F-47, Statements of Operations`). |
| `source_url` | URL (http/https) | yes |  | Public page where the value in this row can be read. |
| `source_name` | text | yes |  | Publisher of that page (outlet, company, regulator). |
| `source_date` | date YYYY-MM-DD | yes |  | Publication date of the source page. |
| `accessed_date` | date YYYY-MM-DD | yes |  | Date we last opened the URL and confirmed the figure. |
| `confidence` | enum | yes | `V`, `R`, `U` | `V` verified, `R` reported, `U` unverified/conflicting (see conventions). |
| `notes` | text |  |  | Verbatim figure as printed, conversions, caveats, conflicts. |

## `data/fx_rates.csv`

Reference FX observations used by every conversion (written by `python -m src.fx --fetch`).

Uniqueness key: `date`, `currency`.

| column | type | req. | allowed values | description |
|---|---|---|---|---|
| `date` | date YYYY-MM-DD | yes |  | Observation date. |
| `currency` | ISO 4217 | yes |  | Currency quoted against USD. |
| `rate` | number ≥ 0 | yes |  | Units of `currency` per 1 USD. |
| `series_id` | text | yes |  | Provider series id (e.g. FRED `DEXCHUS`). |
| `source_url` | URL (http/https) | yes |  | Series page. |
| `source_name` | text | yes |  | Provider. |

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


| item | header | ✓ when | examples |
|---|---|---|---|
| `units` | Units | the company states how many robots it shipped or sold in a full year | Unitree 5,511 ✓; AgiBot "more than 5,100" cumulative ◐; preorders or capacity ✗ |
| `revenue` | Revenue | the company states, or audited accounts give, its annual revenue | 1X: a Norwegian subsidiary's statutory accounts only ◐ |
| `paid_deployment` | At work | the company states how many robots work for paying customers, excluding pilots | AgiBot "more than 300" at one park, counted by the press ◐; Agility gives hours but no count ✗ |
| `hours` | Hours | the company or a filing reports operating hours at paying customers | Agility 65,000+ hours ✓; Figure's BMW pilot hours via a secondary report ◐ |
| `customer` | Customer | a purchase, order or commercial agreement with a named customer, stated by the company, the customer or a filing (pilots included) | Figure–BMW ✓ (pilot); Unitree's sales to Galbot in its prospectus ✓; a press report only ◐ |
| `related_parties` | Rel. party | the share or amount of sales to related parties is disclosed | Agility 63.5% ✓ |
| `audited` | Audited | the company is listed or files audited statements (e.g. with the SEC) | Tesla ◐: group accounts audited, Optimus not reported separately |

# Methodology

This dataset supports *Physical AI, by the Numbers #1 — "Volume in China, Valuation in America"*.
It measures three things about the humanoid robot market: how many robots are shipped, how the
companies that make them are valued, and how much public evidence exists that the robots do useful
work. Data cut-off: **2026-10-12**.

## Scope

**Included**
- Humanoid robot makers, including wheeled dual-arm "humanoids" that their makers and the press
  classify as humanoid robots.
- Laboratories building foundation models for robots.
- Companies that supply training data, simulation or tooling for physical AI.
- Corporate humanoid programmes, recorded as `big_tech_program` (Tesla Optimus, Boston Dynamics/Hyundai).

**Universe rule.** A company is listed when it is in one of the segments above and either:
- has a publicly reported financing round of US$100 million or more since 2025-01-01, or
- appears in Omdia's 2025 ranking of humanoid shipments.

The companies in the seed list for this study are also included.

**Excluded.** Industrial robot arms and collaborative robots, autonomous mobile robots, drones and
defence autonomy, construction and mining equipment, and robots that are not humanoid (for example,
The Bot Company, whose robot is a base with grippers).

## Sources and verification

- **Public sources only.** Every row cites one public page in `source_url`. Paid databases are used
  only through figures their publishers released publicly (for example PitchBook News, Crunchbase News).
- **Every URL was opened** and the figure confirmed on 2026-10-12 (`accessed_date`). The wording of
  the source is kept in `notes`. When a cited page did not support a figure, a page that does was
  found and cited instead.
- **Confidence grades.**
  - `V` (verified): a primary source (company, regulator, exchange, the data provider's own
    publication) or a major outlet reporting the figure as fact.
  - `R` (reported): unnamed sources, deals in talks, self-reported figures that were not audited, or
    secondary aggregators only.
  - `U` (unverified or conflicting): sources disagree, or a page contradicts itself.
- **One row per source, when it matters.** A second source gets its own row only when it adds a
  number or disagrees; otherwise it is named in `notes`. Conflicting figures are never averaged or
  dropped: they are kept side by side and listed in `GAPS.md`.
- **Undisclosed is not zero.** A missing value is an empty cell. When a source gives words instead of a
  number ("a few hundred"), the words are stored in a `*_text` column and the number is left empty.
- **Qualifiers.** "More than", "about" and "up to" are stored in `*_qualifier` columns (`gt`,
  `approx`, `lte`, …) rather than turned into exact numbers. Charts print the matching symbol.
- **Dates.** Event dates may be reduced-precision ISO dates (`2025` or `2025-12`) when the source
  gives no day; the missing part is never invented.

## Currency

- All conversions use the Federal Reserve's H.10 noon buying rates (via FRED), stored in
  `data/fx_rates.csv`, at the rate of the **event date**:
  - the announcement date for a funding round;
  - the valuation date for a market capitalisation;
  - the last day of the reporting period for revenue and profit.
- When H.10 has no rate that day (weekend, US holiday), the latest earlier rate is used, never an
  interpolated one.
- For reduced-precision dates, the last rate of that month or year is used (`src/fx.py`).
- Converted figures from the press are not copied, because outlets use different rates.

## Valuations

- **Private companies:** the most recent round that is closed or announced. An explicit post-money
  figure is preferred, then a valuation whose basis is not stated, then pre-money. Charts call all of
  these "funding round"; the pre/post basis stays in the data.
- **Rounds still in talks or at term-sheet stage** are kept separately: charts list them in the notes
  and never use them as the valuation.
- **Listed companies:** market capitalisation on **2026-09-30**, computed as the official closing price
  × total shares outstanding on that date. The column `calculation` names the source of each input:
  - UBTech: HKEX Daily Quotations × the HKEXnews Monthly Return.
  - Unitree: Shanghai Stock Exchange close × shares from the SSE listing notice.

  Total shares include shares that do not trade (UBTech's unlisted domestic shares, Unitree's
  founder shares). UBTech's value on H shares only is given in `notes`.
- Tesla's Optimus programme has no stand-alone valuation and is not valued.

The rule is implemented once, in `charts/data.py`, and used by every chart.

## Units shipped

- **Omdia's 2025 shipment estimates are the primary figure** for the text and for every derived ratio
  (market shares, valuation per robot, forecast multiples), because Omdia applies one definition to
  every maker.
- Company-reported figures stay in the data and appear in chart 2 as a lighter extension of the bar:
  - Unitree: 4,200 per Omdia (primary) vs 5,511 per its final prospectus.
  - UBTech: 1,000 per Omdia (primary) vs 1,079 per its annual results.
- Shipments, deployments, production, capacity and preorders are different metrics and are never
  added together.
- Cumulative and year-to-date figures carry an `as_of` date.

## Valuation per robot shipped

`python -m analysis.valuation_per_unit` writes `outputs/valuation_per_unit.csv`: the latest valuation
divided by Omdia's 2025 shipments, for every humanoid maker that has both. Robot AI labs ship no robots,
and Tesla's Optimus has no valuation of its own, so neither is included. Where the company reports its
own count, a sensitivity column divides by that count instead (Unitree 5,511, UBTech 1,079); when the
count is a lower bound, the result is an upper bound.

Read it as an **order of magnitude, not a multiple**:

- it divides a point-in-time valuation by one year of shipments (a flow);
- valuation bases and dates differ (funding round, stock market value on 30 Sep 2026, SPAC merger value);
- AgiBot's valuation dates from March 2025 and likely understates its current value;
- the US makers' units are Omdia estimates (150 each for Figure AI, Agility Robotics and Tesla); the
  companies disclose no count.

Each row lists the input rows it uses (`rows_used`, as `file.csv:line`).

## Forecasts

- `annual_revenue` is used only when the publisher says the figure is annual revenue.
- "Market" or "TAM" figures whose basis is not stated are coded `market_size`. Their scope, in the
  publisher's words, is in `scope_definition`.
- Forecasts are comparable only within a target year.

## Prices and costs

- `year` is the year a price was quoted, or the year an estimate refers to.
- `product_class` separates full-size humanoids, compact models and generic analyst estimates, which
  are not directly comparable.

## Evidence of useful work

`deployment_evidence.csv` records each public claim that humanoid robots work for a customer (output
supported, hours, parts handled, orders) and who stands behind it:

| verification | who stands behind the claim |
|---|---|
| `regulatory_filing` | a regulatory filing |
| `customer_statement` | the customer |
| `company_statement` | the maker |
| `third_party_report` | the press |

Negative evidence (no robots doing useful work) is kept.

## Charts

- **Palette.** One palette, defined only in `src/style.py`: slate for the United States, amber for
  China, a muted violet for other countries.
  - It was checked with a colour-vision validator (simulated colour blindness, OKLab ΔE) on the chart
    background.
  - Every amber mark has a direct text label, because amber has low contrast on the background.
- **Encoding.**
  - Robots shipped: Omdia's estimate as a solid bar; a lighter extension runs to the company's own count.
  - Values a company does not disclose are written as "not disclosed", never drawn as zero.
  - Deals not closed are left out of the charts and listed in the notes.
  - Hatching: year to date.
  - Prices: circles are list prices of products on sale; squares are estimates or targets.
- **Annotation.** Each chart has direct labels, one takeaway of at most 15 words, and notes with one
  idea per line (sources, definitions, what is not shown).

## Quality checks

| command | what it checks |
|---|---|
| `python -m src.validate` | types, allowed values, dates, sources, foreign keys, FX consistency, duplicates; runs in CI on every push |
| `python -m pytest` | that the validator catches each error type, plus the FX and label rules |
| `python -m analysis.article_figures` | recomputes every figure the article cites from `data/`, with the rows it uses |

Single line items from filings (sales to related parties, stock compensation, cash, going-concern
language) live in `company_financial_items.csv` with the text quoted verbatim and its page; the
validator rejects a row whose number is not printed in its quote.
| `python -m src.check_urls` | that every cited page still answers; hosts that block scripts are checked by hand and dated |

## Known limitations

See `GAPS.md` for values that could not be sourced and conflicts between sources.

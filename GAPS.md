# Gaps and conflicts

Every value we could not source, or where sources disagree, is listed here with
what was tried. An empty cell in `data/` means "not disclosed / not found" and
should have an entry below if it matters for a chart.

Status: `resolved` (sourced; row added) · `closed-unavailable` (searched up to the data cut-off,
no public source found; left blank or kept at a lower confidence grade, and can be updated in a
later version).

Last full review: 2026-10-12.

## Research gaps

| # | Item | Status | What was tried | Outcome / row |
|---|---|---|---|---|
| 1 | Robotics VC by year 2022, 2023, 2024 | resolved | Crunchbase News 2026-06-22 article text (no yearly values) and its embedded Infogram chart | `sector_funding`: 2020–2026 values and deal counts from the chart |
| 2 | Humanoid VC 2026 YTD | resolved | PitchBook News 2026-05-15 (read in a browser); Dealroom via Robot Magazine; Tracxn | `sector_funding`: PitchBook '>$5 billion' this year (cut-off not stated). Other trackers give $11B to 2026-10-06 (Dealroom) and $6.61B through September (Tracxn) on different definitions; not mixed into the PitchBook series |
| 3 | AgiBot: company-stated 2025 shipments, valuation in USD, IPO status | resolved (2026-10-12, round 2) | Gasgoo 2026-07-28; The Paper 2025-08-01; The Standard 2026-07-24; 21st Century Business Herald | Valuation resolved: RMB 15B after the Tencent-led Series B (Mar 2025), converted. IPO: Hong Kong process reported launched on 2026-07-24; target values (HK$40-50B, US$20B) come only from unnamed sources and are not recorded. Shipments: vice president Zhu Jie gave 'more than 5,100' cumulative to end-2025 (Jiemian, 2026-01-05); no full-year figure, so Omdia's 5,168 stays primary. Revenue: RMB 1.05B in 2025, stated by the CEO (IT之家, 2026-04-17). No prospectus published as of the cut-off |
| 4 | Tesla Optimus official 2025/2026 production | closed-unavailable | Electrek 2026-04-22 (Q1 2026 call); humanoid.guide 2026-07-19 | Tesla has published no production count. Recorded instead: Omdia's 2025 estimate (150), 'a few hundred' mid-2025 output reported by The Information (`R`), and Musk's January 2026 remark that no Optimus was doing useful work (`deployment_evidence`) |
| 5 | Figure AI disclosed unit count or revenue | closed-unavailable | The Robot Report 2026-06-29 (BMW deployment); humanoid.guide | Figure discloses neither. Recorded instead: Omdia's 2025 estimate (150) and BMW's statement that Figure 02 supported production of more than 30,000 X3 vehicles |
| 6 | UBTech market cap (HKEX) on a fixed date | resolved | HKEX Daily Quotations; Monthly Return for September 2026; aggregators and press compared | `valuations_revenue`: 2026-09-30, HK$74.35 x 503,401,373 total shares (derived, both inputs cited) |
| 7 | Primary sources: Skild AI Jan 2026 round; Genesis AI seed | resolved | skild.ai/blogs/series-c; TechCrunch 2025-07-01 + company release | Rows now cite the primary/major-outlet pages |
| 8 | Verify Humanoid (UK) Series A and Mecka Series B | resolved | thehumanoid.ai announcement 2026-07-21; mecka.ai/news/series-b 2026-10-07 | Both confirmed; rows cite company pages |
| 9 | Other Omdia top-10 Chinese makers with 2025 units | closed-unavailable | SCMP 2026-01-09 | Omdia ranks Leju Robotics, Engine AI and Fourier Intelligence 4th-6th without unit counts, and does not name ranks 7-10 publicly. The three are listed in `companies` with no shipments |
| 10 | Physical Intelligence 2026 round: closed? | resolved | Forge record (read in a browser); PitchBook profile; company blog | Series C 2026-05-21, $1.05B at $11.19B post-money per Forge (`R`); not announced by the company |
| 11 | Skild AI Series B terms | closed-unavailable | Pittsburgh Startup News; Bloomberg via Benzinga 2025-06-16; Reuters/PitchBook 2025-12-08; re-checked 2026-10-12 | Never announced by the company; reports differ ($4.5B vs $4.7B). Row kept as `U`. No round after January 2026 as of the cut-off |
| 12 | HQ for Physical Intelligence; Genesis AI dual HQ; ownership status of Leju, Engine AI, Fourier | closed-unavailable | Cited source pages | Not stated in the cited sources; Genesis AI has offices in Paris and Palo Alto and is coded US. Rows kept as `R` |
| 13 | Unitree prospectus (primary document) | resolved (2026-10-12, round 2) | Final prospectus dated 2026-08-14 on cninfo (also on SSE) | Revenue, net profit and 2025 humanoid shipments now cite the final prospectus (5,511 shipped). The earlier Wallstreetcn summary of a draft gave RMB 1,708M revenue and RMB 288M profit; the final figures are RMB 1,699M and RMB 278M |
| 14 | 1X NEO price and preorders from a primary page | closed-unavailable | The Cryptonomist (AI-assisted article) | No primary page with both figures found; rows kept as `R` |
| 15 | Agility Robotics revenue and losses from its SEC filings | resolved | Form S-4/A (Amendment No. 1) filed 2026-09-30 | `valuations_revenue`: audited FY2024 and FY2025, unaudited H1 2026. No total count of deployed robots is disclosed |
| 16 | Figure's November 2025 report on the BMW deployment (hours, parts, accuracy) | resolved (2026-10-12, round 2) | figure.ai/news/production-at-bmw (2025-11-19) | Hours (1,250+) and parts (90,000+) now cite Figure's page (`V`); no robot count on the page |

## Conflicts kept on purpose

| Item | Sources | Values | How charts handle it |
|---|---|---|---|
| Unitree 2025 humanoid shipments | Final prospectus (p. 1-1-145); Omdia; Counterpoint | 5,511 shipped, 5,215 sold (company); 4,200 (Omdia); ~4,224 installations (Counterpoint) | Omdia primary for ratios and text; company figure shown as range in c02 |
| Unitree market cap, first trading day | The Paper; Fortune | RMB 341.8B at the close; "around $66 billion" (≈ opening price) | Close (The Paper); Fortune row kept as `U` |
| Unitree 2025 profit | Final prospectus; Wallstreetcn (draft); Fortune | Net profit RMB 278M (final); RMB 288M (draft summary); adjusted RMB 591M ("600 million yuan in profit" in Fortune) | Reported net profit, final prospectus |
| Skild AI Series B valuation | Pittsburgh Startup News; Reuters/PitchBook | $4.5B vs $4.7B | Row `U`; not charted as primary |
| Dyna Robotics round type | Company; CO/AI | Series A vs Series B | Company (Series A) |
| Agility SPAC valuation basis | Company release via Pulse 2.0; Crypto Briefing | $2.5B pre-money equity vs "approximately $2.5B" | Pre-money (company) |
| Apptronik Series A size and 2026 valuation | Bloomberg; company; Crunchbase | $350M → $403M → $415M; >$5.5B (Bloomberg) vs "over $5 billion" (PitchBook, citing CNBC and Bloomberg, same day) vs ~$5B (SEC filing per Crunchbase) vs undisclosed (company) | $415M; >$5.5B labelled "reported" |
| Unitree G1 list price | AI Business; Fortune; Bloomberg via Business Standard | $13,800 (2025); $13,500 (2026); $16,000 (2025) | Lowest current list price, others noted |
| Morgan Stanley 2050 installed base | Same page | "more than 1 billion" vs "nearly 1 billion" | ~1B, `U` |
| Goldman Sachs 1.4M units (2035) | Same page | Annual vs cumulative not stated | `U`; excluded from annual comparisons |
| UBTech market cap, 2026-09-30 | HKEX quote page; Futu, Morningstar; stockanalysis.com, Investing.com | H shares only (438.2M shares) vs total shares (503.4M) vs 502.6M (total minus incentive-trust shares, undocumented) | Total shares; H-only value in notes |
| Agility 2025 costs | June 2026 investor deck (8-K) vs audited S-4/A | Operating expenses $111M (preliminary, unaudited) vs $137.5M (SG&A + R&D, audited); Startup Fortune's "$37 million" revenue vs audited $1.78M | Audited S-4/A figures |
| Unitree market value in USD | SCMP, The Robot Report, Bloomberg | Implied CNY/USD rates between 6.71 and 7.13 | Federal Reserve H.10 rate of the valuation date |
| Humanoid VC by provider | PitchBook; Dealroom (via Robot Magazine); Tracxn | 2025: $6.1B vs $4.8B vs $3B; 2026 YTD: >$5B (mid-May) vs $11B (to Oct 6) vs $6.61B (to Sep) | PitchBook only, for continuity with 2019-2025 |
| UBTech 2025 humanoid units | Omdia (via SCMP); UBTech annual results | 1,000 vs 1,079 ('sales volume', full-size) | Omdia primary for ratios and text; company figure shown as range in c02 |

## Disclosure scorecard: cells marked ✗ or ◐

`outputs/disclosure_scorecard.csv` marks a cell ✗ when the item was not found in public sources as of
2026-10-12. On 2026-10-12 each company was checked for about 15 minutes per item beyond this dataset's
own sources: company newsrooms and releases, exchange filings (cninfo, HKEXnews, SEC EDGAR, the Norwegian
register), and Chinese and English press. What was found and kept out, and why:

| Company | Item | Found | Why ✗ or ◐ |
|---|---|---|---|
| All ten | Robots at work | No company-wide count of robots working for paying customers | AgiBot ◐: "more than 300" robots of all product lines at Chimelong Spaceship Park, bought, counted by the reporter (Xinhua Finance, 2026-10-05) |
| Figure AI | Robots at work | CEO: "six or eight" robots at BMW and "I think we're getting paid" (Forbes, October 2026) | BMW told Forbes the 2026 project was a non-production test of two or three robots that has ended; contested, not counted |
| Figure AI | Units, revenue | "over 350" Figure 03 robots delivered (figure.ai, 2026-04-29), no period and partly internal | Not 2025 shipments; Figure declines to disclose revenue (Forbes) |
| Tesla | Units, revenue, robots at work | 10-K FY2025: "We have yet to commercialize Bots"; two reportable segments (automotive, energy) | No Optimus sales, revenue line or external customer; Musk said in January 2026 that no Optimus was doing useful work (Electrek, in `deployment_evidence`) |
| 1X Technologies | Units, customer | Preorders that "booked out" 10,000 units of capacity (1x.tech, 2026-04-30); non-binding EQT intent for up to 10,000 robots (2025-12-11) | Preorders and intents are not shipments or orders; no delivery announced |
| Galbot | Units, robots at work | "reportedly" 1,200 G1 shipped (Gelonghui, 2026-01-29); "nearly 100" at CATL (PEdaily, 2026-06-25) | Both unattributed; not company statements |
| X Square Robot | Units, revenue, customer | COO: January shipments exceeded all of last year (TMTPost, 2026-09-19); 58.com home-cleaning service launch (PR Newswire, 2026-03-18) | No number; 58.com is a channel partner, not a buyer of robots |
| Apptronik | Robots at work | "commercial and pilot deployments" (2026-02-11); press: "a handful" at Mercedes-Benz | No count from the company |
| UBTech | Robots at work | 1,079 full-size humanoids sold in 2025; Walker S2 "small-scale mass production and delivery" | Sales, not a count of robots at work; related-party sales are in the Annual Report (p. 283), not the results announcement |
| Unitree | Robots at work, hours | Prospectus: humanoids "mostly remain at the application-scenario validation/testing stage" (p. 1-1-138) | No count of robots at customers; hours only as battery specifications |
| AgiBot, Galbot, X Square, Figure, Apptronik | Audited accounts | No published prospectus or filing (AgiBot's Hong Kong IPO launched 2026-07-24; none filed by the cut-off) | Private |

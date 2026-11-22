# Board backlog: triage log

Every actionable idea from the knowledge notes, and what was decided for the Entry/Exit Board. Rules are in the [knowledge README](README.md#how-ideas-are-triaged). Newest week first.

**Open candidates:** 6 · **Built:** 3 (1 flag, 1 scored input, 1 display) · **Checked against data:** 1

**Next to build, in order:**
1. #19, a peak-margin guard for cyclicals.
2. #17b, thematic NFOs by theme. Needs scheme-level launch data.

Everything else is blocked on data.

## Built

| Idea | Built on | What shipped | Result |
|---|---|---|---|
| Distance from high (#20) | 2026-11-22 | `scripts/fetch_parabolic.py` also computes, from the same 10-year daily closes, the fall from the 10-year high, time since that high, how unusual today's fall is (share of days since 2016 that were further below the high), the worst fall and its date, and the longest stretch below a high. Shown as "Distance from high" in the panel of all 97 assets with daily data. **Display only, no score change.** | First reading (20 Nov 2026): IT −32% (1.9 years since its Dec 2024 high; only 6% of days since 2016 were deeper) next to a sector score of 27.9; FMCG −27% (4%); silver −64%, its deepest point since 2016; PSU Bank at a new high after a −73% fall in 2020. |
| Thematic-fund froth (#17) | 2026-11-22 | `scripts/fetch_amfi_thematic.py` reads AMFI's monthly report (open-ended equity section; "Sectoral/Thematic", split into "Sectoral" and "Thematic" in 2025) and keeps `models/amfi-thematic-monthly.csv` (Apr 2019 onward, 91 months). Runs daily from `fetch_prices.py`, standard library only, and downloads only new months. The sectors model scores it as **S4** (Sector cycle bucket, weight 5.1): the mean own-history percentile of 3-month inflow ÷ equity AUM, share of equity inflows, and 6-month rise in scheme count. Applies to the five size indices plus CPSE, Defence and Infra. On the board: a panel section on those indices, an alert at 80+, and a history chart on the Alerts tab. **Changes scores.** | Back-check (`scripts/research/amfi_froth_test.py`): after months in the top third of thematic buying, the Nifty 500 returned a median +4–5% over 12 months, against +15–28% after the bottom third; the Jul–Aug 2024 peak was followed by −12% to −16% over 6 months. One cycle with overlapping windows, so the weight is kept modest. Today's reading is 24 (low), which moved 8 indices down 0.1–3.6 points: Smallcap 250 Trim → Hold, Midcap Select Hold → Accumulate. |
| Parabolic move (70%+ above the 150-day EMA) | 2026-11-22 | `scripts/fetch_parabolic.py`, run daily by the refresh Action (started from `fetch_prices.py`), writes `data/parabolic.json`. 97 assets: gold, silver, Brent, copper, Bitcoin, Nifty 50, 13 Nifty sector indices, the Nifty 50 stocks, 19 global indices, 7 listed REITs and InvITs. Shown in each item's panel and on the Alerts tab, with a back-test card. **Does not change any score.** | Back-test on ~10 years of daily prices: 12 episodes in 7 assets (mostly Bitcoin and Indian stocks in 2020–21; never an equity index). Prices were usually *higher* afterwards: median +16% after 3 months, +60% after 6, +80% after 12; lower in 17%, 25% and 36% of cases. Silver in January 2026 was the clean hit (−38% in 6 months). Verdict: a late-stage volatility warning, not a sell signal, so it stays a flag. Revisit if it is ever combined with a valuation score above 65. |

No Yahoo history for Nifty Private Bank, Midcap 150, Smallcap 250, Midcap Select, CPSE and Defence, the factor indices, CSI 300, MOEX, Tadawul and WIG20, so these have no flag yet.

## Research batch, 2026-11-22: desk research on sector investing

Notes:
- [What the research says](sector-rotation-research-evidence.md)
- [Sector froth signals](sector-froth-signals.md)
- [Valuing cyclical sectors](valuing-cyclical-sectors.md)
- [India sector facts 2016–2026](india-sector-facts-2016-2026.md)
- [Playbook](sector-investing-playbook.md)

| # | Idea | Decision | Where it would go | Why / blocker |
|---|---|---|---|---|
| 17 | **Sectoral/thematic fund flows and NFO collections** as froth (market-wide), and **thematic NFOs by theme** (sector-level) | **Built (market-wide part), 2026-11-22**; theme-level part open as #17b | Nifty 50 model and size indices: a froth input next to the existing small/mid MF inflow indicator. Sectors model: an NFO-cluster input in the Sector cycle bucket for the matching theme (defence, PSU, infra, healthcare, consumption). | Strongest evidence of the batch: thematic ETFs lost about 30% risk-adjusted over five years after launch (Ben-David et al.), sector funds have the widest investor-return gap (Morningstar), and India's June 2024 record was followed by −16% three-year category returns. Data is free monthly from AMFI (PDF and Excel). Replaces item 2's missing data source at the theme level. To do: parse the AMFI monthly Excel, build a history back to 2019, and set percentile anchors. |
| 18 | **RBI policy direction** (easing vs tightening) tilts cyclicals vs defensives | **Board: candidate** | Sectors model, Sector cycle bucket for the deep-cyclical and defensive families | One US study (1973–2005) found 2–5% a year. Blocker: check first whether C4 (Nifty 50 Timing import) already carries the rate signal, and test on Indian sector data since 2016 (only about 3 easing and tightening phases, so weak evidence). |
| 19 | **Peak-margin guard for cyclicals:** a low P/E on top-decile margins is not cheap | **Board: candidate** | Sectors model, deep-cyclical family: cap C1/C12's "cheap" contribution when operating margin is in the top decile of its 10-year range | Directly prevents the classic cyclical trap (graphite electrodes 2018, metals at commodity peaks). Blocker: needs a 10-year operating-margin history per sector index. |
| 20 | **Drawdown from high and years below it,** shown in each sector's panel | **Built, 2026-11-22** (display only; all 97 assets with daily data) | Sector drawer, next to the parabolic check | Gives context for Buy readings on beaten-down sectors (IT −32%, FMCG −27% today). Uses the daily history the parabolic check already downloads. No score change. |
| 21 | Long-term industry reversal (3–5 years) | **Already covered** | C8 and C16, contrarian | Supported by UK, US and our India data. No change. |
| 22 | Value cyclicals on P/B or normalised earnings | **Already covered** | C1 uses P/B for banks, PSU banks, metal, energy, realty; C12, C15 | No change. |
| 23 | Credit cycle (credit growth, GNPA) drives bank stocks | **Already covered** | Banking module (design §5.2) | The 2018 NPA peak and 2022 PSU Bank surge line up with it. |
| 24 | Business-cycle phase rotation | **Knowledge only** | — | About 2% a year with perfect foresight; nil after costs and timing errors. |
| 25 | Momentum crashes after market falls | **Knowledge only** | — | Matters only if a momentum overlay is ever added. |
| 26 | Nifty 50 concentration in financials (33–38%) | **Knowledge only** | — | An allocation point, not entry/exit timing. |
| 27 | Returns on capital by industry persist for decades | **Already covered** | Own-history anchors per index | Explains why each sector is scored against its own range. |

## Week of 2026-11-22, second batch: three sector-rotation videos

Notes: [Flat markets are not dead markets](flat-markets-are-not-dead-markets.md) (WeekendInvesting) · [Identifying winning sectors](identifying-winning-sectors.md) (ET Money) · [Sector rotation through the economic cycle](sector-rotation-economic-cycle-schwab.md) (Charles Schwab)

| # | Idea | Decision | Where it would go | Why / blocker |
|---|---|---|---|---|
| 10 | **Follow sector strength (momentum):** all three videos say to rotate into the sectors that are leading | **Checked against data: model unchanged** | Sectors model C8 (6-month relative strength vs Nifty 50), scored as contrarian | Tested on 13 Nifty sector indices, Nov 2016 to Nov 2026 (`scripts/research/sector_momentum_test.py`). Ranking by 6-month strength, the top third beat the bottom third by only −0.2 to +1.0 pp over the next 1–6 months (no real momentum), and *trailed* by 4.0 pp over the next 12 months. Ranking by 12-month strength, the top third trailed by 6.5 pp over 12 months and 7.3 pp over 36. For a holding period of up to 5 years, the contrarian reading in C8 is right. Caveat: overlapping windows and 13 indices, so it is indicative only. |
| 11 | **Sector growth as a multiple of nominal GDP growth:** above GDP is a tailwind; 5–6 times GDP is growth borrowed from the future | **Board: candidate** | Sectors model, as a Sector cycle or Filter input next to C14 (TTM EPS growth) | Adds a scale that works across sectors and links to the earnings-led bubble idea from the first note. Blocker: needs quarterly aggregate revenue per sector index; the stocks model covers only 50 names today. |
| 12 | Sector P/B premium to Nifty 500 against its own median | **Already covered** | Sectors model C3 (relative P/E vs Nifty 50, z-score vs 10-year mean) | Same idea on a different metric. Possible later refinement: use P/B for financials, as C1 already does. |
| 13 | Business-cycle phase decides which sectors lead (financials and cyclicals early, defensives late) | **Already covered / knowledge** | C4 imports the Nifty 50 model's Timing bucket; family weights already treat defensives differently | The neat US sequence does not hold well in India (autos and pharma led one flat phase and lagged the next). No separate phase model. |
| 14 | Defensives win long flat phases | **Knowledge only** | — | Only two past flat phases (2008–14, 2018–21); too few for a rule. |
| 15 | Earnings beats against estimates | **Knowledge only** | — | Needs paid consensus-estimate data (fails test 4). |
| 16 | Sunrise themes, policy cycles, seasonality (ACs, hotels, fertilisers) | **Knowledge only** | — | Stock and theme ideas outside the board's indices. |

## Week of 2026-11-22: [Sector rotation: 7 Indian bull runs](sector-rotation-7-indian-bull-runs.md)

| # | Idea | Decision | Where it would go | Why / blocker |
|---|---|---|---|---|
| 1 | **Parabolic move:** price more than 70% above its 150-day EMA marks euphoria | **Built as a flag** (2026-11-22) | See "Built" above | The back-test showed it is not a reliable sell signal on its own, so it does not move scores. |
| 2 | **Issuance froth:** a cluster of IPOs and QIPs in one sector signals a peak | **Board: candidate** | Sectors model, Sector cycle bucket, extending the existing "IPO + SME issuance" indicator (design §5.1, size indices only) to the thematic and cyclical families | Fits the capital-cycle logic. Blocker: no free monthly source that counts issues by sector; NSE and Prime Database lists would need manual tagging each month. |
| 3 | **Rate of change of growth:** when revenue growth keeps slowing (for example 50–60% down to 15–20%), a richly valued stock de-rates | **Board: candidate** | Nifty 200 stocks model, as an exit-side indicator (2–4 quarter change in revenue growth), weighted more when the stock's P/E is high against its own history | Directly an exit signal. Blocker: needs 4–6 quarters of revenue per stock in the inputs file; today the model holds one snapshot. |
| 4 | **Cycle length** (long, medium or short) decides how long to stay with a sector | **Board: candidate** | A per-index field in `nifty-sectors-config.json`, shown in the drawer and used to stretch or shorten the "Trim into rallies" advice | Changes how long to hold, which the board doesn't express today. Blocker: needs a rule for which sector gets which length that isn't pure opinion. |
| 5 | Breadth: 90–95% of stocks above their 200-day average signals market euphoria | **Already covered** | Sectors model euphoria veto (% of members above 200-DMA ≥85% plus index ÷ 200-DMA ≥1.15) | No change. The video's 90–95% market-wide reading is consistent with the existing threshold. |
| 6 | Sector P/E against its own long-term range | **Already covered** | Valuation bucket of the sectors and Nifty 50 models (own-history percentiles) | No change. |
| 7 | Relative strength score above 75 to spot new leaders | **Knowledge only** | — | A stock-screening tool for finding themes beyond the board's 20 indices. The sectors model already has a Relative output for the indices it scores. |
| 8 | Capital-cycle stages for specific industries (hotels, transformers, cables, paints, solar, smart meters) | **Knowledge only** | — | Industry calls outside the board's indices, and they are the presenter's opinion. Useful context for stock research. |
| 9 | Valuation-led vs earnings-led bubbles; the seven bull runs and their leaders | **Knowledge only** | — | Frameworks and history. Worth re-reading when a sector score sits at an extreme. |

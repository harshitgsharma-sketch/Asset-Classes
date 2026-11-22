# Board backlog: triage log

Every actionable idea from the knowledge notes, and what was decided for the Entry/Exit Board. Rules are in the [knowledge README](README.md#how-ideas-are-triaged). Newest week first.

**Open candidates:** 3 · **Built:** 1 (as a flag)

## Built

| Idea | Built on | What shipped | Result |
|---|---|---|---|
| Parabolic move (70%+ above the 150-day EMA) | 2026-11-22 | `scripts/fetch_parabolic.py`, run daily by the refresh Action (started from `fetch_prices.py`), writes `data/parabolic.json`. 97 assets: gold, silver, Brent, copper, Bitcoin, Nifty 50, 13 Nifty sector indices, the Nifty 50 stocks, 19 global indices, 7 listed REITs and InvITs. Shown in each item's panel and on the Alerts tab, with a back-test card. **Does not change any score.** | Back-test on ~10 years of daily prices: 12 episodes in 7 assets (mostly Bitcoin and Indian stocks in 2020–21; never an equity index). Prices were usually *higher* afterwards: median +16% after 3 months, +60% after 6, +80% after 12; lower in 17%, 25% and 36% of cases. Silver in January 2026 was the clean hit (−38% in 6 months). Verdict: a late-stage volatility warning, not a sell signal, so it stays a flag. Revisit if it is ever combined with a valuation score above 65. |

No Yahoo history for Nifty Private Bank, Midcap 150, Smallcap 250, Midcap Select, CPSE and Defence, the factor indices, CSI 300, MOEX, Tadawul and WIG20, so these have no flag yet.

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

# Board backlog: triage log

Every actionable idea from the knowledge notes, and what was decided for the Entry/Exit Board. Rules are in the [knowledge README](README.md#how-ideas-are-triaged). Newest week first.

**Open candidates:** 4 · **Built:** 0

## Week of 2026-11-22: [Sector rotation: 7 Indian bull runs](sector-rotation-7-indian-bull-runs.md)

| # | Idea | Decision | Where it would go | Why / blocker |
|---|---|---|---|---|
| 1 | **Parabolic move:** price more than 70% above its 150-day EMA marks euphoria | **Board: candidate** (first in line) | A timing-bucket flag in the gold, silver, Bitcoin and commodities models, and a third condition on the sectors model's euphoria veto | Measurable from daily prices and cheap to compute. Blocker: the repo fetches spot prices only, so it needs about 150 days of price history per asset, and a check of how often the threshold fired in the past (silver 2025–26, 2021 stocks) before it can move a score. |
| 2 | **Issuance froth:** a cluster of IPOs and QIPs in one sector signals a peak | **Board: candidate** | Sectors model, Sector cycle bucket, extending the existing "IPO + SME issuance" indicator (design §5.1, size indices only) to the thematic and cyclical families | Fits the capital-cycle logic. Blocker: no free monthly source that counts issues by sector; NSE and Prime Database lists would need manual tagging each month. |
| 3 | **Rate of change of growth:** when revenue growth keeps slowing (for example 50–60% down to 15–20%), a richly valued stock de-rates | **Board: candidate** | Nifty 200 stocks model, as an exit-side indicator (2–4 quarter change in revenue growth), weighted more when the stock's P/E is high against its own history | Directly an exit signal. Blocker: needs 4–6 quarters of revenue per stock in the inputs file; today the model holds one snapshot. |
| 4 | **Cycle length** (long, medium or short) decides how long to stay with a sector | **Board: candidate** | A per-index field in `nifty-sectors-config.json`, shown in the drawer and used to stretch or shorten the "Trim into rallies" advice | Changes how long to hold, which the board doesn't express today. Blocker: needs a rule for which sector gets which length that isn't pure opinion. |
| 5 | Breadth: 90–95% of stocks above their 200-day average signals market euphoria | **Already covered** | Sectors model euphoria veto (% of members above 200-DMA ≥85% plus index ÷ 200-DMA ≥1.15) | No change. The video's 90–95% market-wide reading is consistent with the existing threshold. |
| 6 | Sector P/E against its own long-term range | **Already covered** | Valuation bucket of the sectors and Nifty 50 models (own-history percentiles) | No change. |
| 7 | Relative strength score above 75 to spot new leaders | **Knowledge only** | — | A stock-screening tool for finding themes beyond the board's 20 indices. The sectors model already has a Relative output for the indices it scores. |
| 8 | Capital-cycle stages for specific industries (hotels, transformers, cables, paints, solar, smart meters) | **Knowledge only** | — | Industry calls outside the board's indices, and they are the presenter's opinion. Useful context for stock research. |
| 9 | Valuation-led vs earnings-led bubbles; the seven bull runs and their leaders | **Knowledge only** | — | Frameworks and history. Worth re-reading when a sector score sits at an extreme. |

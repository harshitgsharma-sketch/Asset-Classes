# Nifty 500 Stock Screener — Scoring Design (v1, indicative, 21 Nov 2026)

**Update 22-Nov-2026:** the target universe is now the Nifty 500. Non-Nifty-50 stocks come from Yahoo Finance via `scripts/fetch_stock_fundamentals.py` (see run procedure §6) and are auto-classified: NSE industry → sector index (IT, FMCG, Pharma, Auto, Metal, Energy, Realty, Infra, Consumption, Fin Services; banks → Private/PSU Bank; other → Nifty 500), Yahoo industry → type (banks and credit = lender, insurance = insurer).

**Status (v1):** v1 engine built and run on the 50 Nifty 50 constituents (as of 30-Sep-2026) with data to 20-Nov-2026. The target universe is the Nifty 200; the engine accepts the other 150 as extra rows in the inputs CSV (see §6). Score only with `claude/stock_oscillator.py` + `claude/nifty500-stocks-config.json` + `claude/nifty500-stocks-inputs-monthly.csv`. Results are in `claude/nifty500-stocks-score-log.csv`. Playbook: `claude/nifty500-stocks-run-procedure.md`.

> Not investment advice. Anchors are starting judgments. There is no back-test, so they must be reset from back-tested data.

## 1. Purpose

Each stock gets one score from 1 (cheap, buy) to 100 (rich, sell), on the same engine and bands as the other models: ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit. It is for an INR investor with a holding period of 5 years or less, picking names inside an equity sleeve whose size is set by the Nifty 50, sector and asset-class models. It does not decide whether to own equities at all.

What changes from the index models:
- **Valuation is judged two ways.** One is against the stock's own past (re-rating over 5 years, and PE vs its own 5-yr median once that data is sourced). The other is against its sector, using the sector index PE from the sector model's inputs.
- **Quality replaces macro.** For a single company, ROE, leverage and earnings stability matter more than the macro Timing bucket, which the Nifty 50 and sector models already cover.
- **Momentum is trend-following over 1 year and contrarian over 3 years.** That matches the evidence for individual stocks: 12-month winners tend to keep winning, and 3–5-year winners tend to mean-revert.

## 2. Engine

Same as the Nifty 50 and sector models:
- Per indicator: score = clamp(1 + 99 × (x − cheap)/(rich − cheap), 1, 100). The ends are swapped where high is good, so a high score always means expensive or a headwind.
- Weight W = Impact × Severity × Reliability × Stability. Blank inputs are skipped and weights re-normalised inside each bucket. A missing bucket drops out and the others are re-weighted.
- Thin-bucket rule: a bucket resting on one indicator moves only half-way from 50.

Buckets: **Valuation 50% · Quality 25% · Momentum 25%.**

## 3. Indicators (v1)

| id | Indicator | Bucket | Type | Cheap → Rich | Applies to | v1 status |
|---|---|---|---|---|---|---|
| V1 | PE ÷ sector index PE | V | Leading | 0.6 → 1.8 | all | live (sector PE from `nifty-sectors-inputs-monthly.csv`) |
| V2 | 5-yr re-rating: price CAGR − EPS CAGR (pp/yr) | V | Leading | −10 → +10 | all | live (own-history proxy; skipped when the EPS base year is a loss) |
| V3 | Earnings yield − 10-yr G-sec (pp) | V | Leading | +3 → −5 | all | live (G-sec from Nifty inputs) |
| V4 | P/B ÷ (5-yr ROE ÷ 12.5%) | V | Leading | 0.7 → 2.5 | lenders | live |
| V5 | PE vs own 5-yr median PE (%) | V | Leading | −35 → +35 | all | **not sourced**: column `pe_med5` is ready |
| Q1 | ROE, 5-yr average (%) | Q | Lagging | 25 → 8 (lenders 18 → 8) | all | live |
| Q2 | Debt ÷ equity | Q | Lagging | 0 → 1.5 | non-financials | live |
| Q3 | EPS stability: years of falling or negative EPS in the last 5 | Q | Lagging | 0 → 3 | all | live |
| Q4 | ROE trend: latest − 5-yr average (pp) | Q | Coincident | +5 → −8 | all | live |
| M1 | 1-yr price return − Nifty 50 (pp) | M | Coincident | +30 → −30 | all | live |
| M2 | 3-yr price CAGR − Nifty 50 (pp/yr), reversal | M | Leading | −15 → +15 | all | live |

Stock types (config): `nonfin`; `lender` (banks and NBFCs: adds V4, uses lender ROE anchors, skips Q2); `insurer` and `holdco` (skip Q2, because consolidated borrowings belong to subsidiaries).

## 4. Signals, vetoes and flags

- **Falling knife veto:** if the score is ≤35 and either TTM profit growth is ≤ −20% or Momentum is ≥75, the signal becomes "BUY VETOED – wait".
- **Not rated:** if the Valuation bucket is empty (for example a loss-making stock with a loss-year EPS base), the signal is "NOT RATED". The number is shown but should not be acted on.
- **Value-trap check:** Valuation ≤35 and Quality ≥65.
- **Quality at a price:** Valuation ≥66 and Quality ≤30.
- **Per-stock flags in config:** cyclicals near peak commodity prices, demerger one-offs, holdcos, insurers (P/EV not sourced), tiny book values, and so on.

## 5. Known weaknesses in v1

1. **The own-history measure is a proxy.** V2 says whether the PE has expanded or contracted over 5 years. It does not say where today's PE sits in its own range. V5 fixes this once 5-yr median PEs are sourced.
2. **There is one month of data and no back-test.** Treat 36–65 as neutral.
3. **Sector PE is an index-level, cap-weighted PE.** Stocks that dominate their index (for example Reliance in Energy) are partly compared with themselves.
4. **Cyclicals look cheapest at peak earnings** (metals, ONGC, Coal India). Read their scores with the value-trap flag.
5. **Insurers and holdcos are mis-measured by PE/ROE.** Treat their scores as a placeholder.
6. **Screener.in "Stock Price CAGR" is a price return** (dividends excluded). The Nifty benchmark is also a price return, so the comparison is consistent, but high-yield stocks (Coal India, ITC, ONGC) are understated on momentum by their yield.

## 6. Covering the full Nifty 200

Collecting 200 stocks by web fetch is slow (one page per stock), and 150 more would add a few hours per monthly run. Better sources, in order:
1. **Screener.in screen export.** A free account can save a screen with `Index = Nifty 200` (or a watchlist) and export it to Excel. The columns used here (Price, P/E, Book value, ROE, ROE 5Yr, Profit growth 5Yr, Return over 1/3/5 years, Debt, Equity, 52-wk high/low, and EPS for the last 6 years) are all available as screen columns. Map them to the CSV columns and append rows.
2. **NSE constituent list:** niftyindices.com publishes `ind_nifty200list.csv` (symbol, industry). Use it to add the 150 stocks to the config with `sector_index`. The engine scores unlisted tickers anyway, as nonfin vs Nifty 50, flagged.
3. **Own-history PE (V5):** Screener's PE chart (5-yr median PE) or Trendlyne's PE band. Both need a logged-in export; the chart API is blocked to automated fetch.
4. **P/EV for insurers and SOTP for holdcos:** company investor presentations, quarterly.

## 7. Roadmap

- v1.1: populate the Nifty 200 from an export; add V5 (own 5-yr median PE).
- v1.2: add EPS revisions (falling-knife leg) and a 200-DMA / 52-week-high momentum measure; P/EV for insurers.
- v2: back-test 12-month forward returns by score band from monthly snapshots, then reset the anchors.

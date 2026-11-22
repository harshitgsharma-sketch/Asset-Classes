# Global Indices (Top-20 Economies) — Standard Run Procedure (v1.0, 21-Nov-2026)

> **Release status:** v1.0. 23 markets + MSCI ACWI scored. The Nifty 50 is ranked like any other market.
> - 10 indices have 3–6 valuation inputs from measured history: forward P/E, CAPE and dividend yield vs own history.
> - The other 13 still rest on one valuation input (trailing P/E z).
> - One month of scores, no back-test (§7).
>
> Report as **indicative** and act only at the extremes (≤35 or ≥66).

Applies to any question about equity markets of the top-20 economies, including India: "global score", "entry/exit for 5 years", "is the US expensive", "which markets to buy/trim", "rate markets on valuation". Design: `global-indices-model-plan.md`.

Project files (all under `claude/`):
| File | Role |
|---|---|
| `global-indices-model-plan.md` | Design, universe, improvement roadmap and status |
| `global-indices-run-procedure.md` | This playbook |
| `global_oscillator.py` | Canonical engine. The only scoring code to use |
| `global-indices-config.json` | Per-index set-up: family, access route, cost, weight multipliers, anchor overrides, flags |
| `global-indices-inputs-monthly.csv` | Long format, one row per (month, index), plus GLOBAL and ACWI rows |
| `global-indices-valuation-history.csv` | Raw history: forward P/E, CAPE, dividend yield (latest month first, then year-ends). The engine computes 10-yr norms from it |
| `global-indices-score-log.csv` | Generated scores (regenerated on every run) |
| `global-indices-valuation-log.csv` | Generated valuation-only ranking |

## 1. Steps

1. **Run the Nifty 50 model first** (`nifty-run-procedure.md`). Reuse its month-end HY spread (i18), DXY, Brent, repo, expected repo change (i03) and G-sec values on the GLOBAL and NIFTY50 rows.
2. **Load** all seven data/engine files with `project_read` and write them to a working folder.
3. **Refresh inputs** (§3). Add rows for the new month (copy last month's block, then update). For each index with a history page, **prepend** the new month-end forward P/E, CAPE and dividend yield to the valuation history (newest first) and drop the previous partial-month row. Mark every judgment value "est.".
4. **Run** `python3 global_oscillator.py all`. Use `... drivers DAX KOSPI` for chosen indices and `... valuation` for the valuation-only ranking. Quote only numbers the script prints.
5. **Report** with the §5 template. Send `global-indices-score-log.csv`.
6. **Save back** the inputs, valuation history and both logs (the engine/config only if changed) with `project_write` + `local_path`. Add a §8 run-log line.

A scheduled task ("Asset Mgmt monthly model refresh", 11:13 IST on the 3rd of each month) runs steps 1–6 for all four models automatically.

## 2. Fixed conventions

- **Score:** clamp(1 + 99 × (x − cheap)/(rich − cheap), 1, 100). A high score means expensive or a headwind. Bands: ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit.
- **Weights:** W = I × S × R × St (`SPEC`). Blank inputs are skipped and weights re-normalised within the bucket. A bucket with one indicator moves only half-way from 50.
- **Headline outputs (user preference: absolute, local currency, Nifty 50 ranked like any market, no vs-Nifty column):**
  - **5-yr score** = Valuation 75% + Filter/quality 15% + Macro 10%. Its band is the entry/exit decision for a holding period up to 5 years.
  - **Entry timing** = Timing 60% + Macro 40%. It sets *how* to act, via the entry plan:
    - Buy/Accumulate with price more than 15% below the 200-DMA → enter in thirds over 6–12 m, and speed up once the price recrosses the 200-DMA.
    - Otherwise: timing ≤45 → lump sum acceptable; 45–60 → 3 tranches over ~6 m; >60 → 6 monthly tranches.
    - Hold → no new lump sum.
    - Trim/Exit → trim now if timing ≥60, else trim into rallies.
    - Not investable → watch only.
  - **Expected return** (% p.a. in INR, net of access cost, ±3 pp) = dividend yield (or 50% of the CAPE earnings yield) + real EPS growth (developed 1.5, emerging 2.5) + half the CAPE gap to its 10-yr mean closing over 5 years + India inflation 4% (PPP) − cost.
    - Without CAPE history the reversion term is 0 (flagged).
    - Not computed for high-inflation markets.
- **Secondary (logged only):** `blend_abs_v04` (the v0.4 absolute blend), `inr_blend` (incl. the currency bucket; `table inr`), and `relative` (G4, F4 vs ACWI).
- **Valuation inputs:**
  - G1: trailing PE z vs own 10 yrs (worldperatio).
  - G3: forward PE vs own 10-yr average.
  - G5: CAPE z vs own 10 yrs.
  - G7: dividend yield z (high = cheap).
  - G3, G5 and G7 are computed from the history file; measured history overrides CSV estimates.
  - G2 (ERP) and G4 (relative fwd PE) are pilot-only, with estimated norms.
- **Earnings-cycle check (#5):** if |CAPE z − trailing PE z| ≥ 1, earnings are off-trend. G1 and G3 weights are halved and the index is flagged ("earnings above/below trend").
- **T4 is momentum** (1-yr under-performance vs ACWI = headwind). F4 (3-yr) stays contrarian.
- **Global risk block (T3)** = average of US HY spread, DXY, Fed 6-m path and Brent sub-scores. Weight ×1.25 for EM, ×0.5 for Japan.
- **Vetoes:**
  - Falling knife: 5-yr ≤35 and (Filter ≥70 or EPS revision ≤ −3%).
  - Euphoria: 5-yr ≥66 and price ÷ 200-DMA ≥1.15 (EM 1.20).
- **High-inflation rule** (Turkey): currency judged in real terms; no expected return.
- **Anchors:** each index's own history, never cross-country raw PE.

## 3. Inputs, sources, frequency

| Column / file | Indicator | First source | Freq |
|---|---|---|---|
| pe, pe_z5/10/20, dma200 | G1, T1 | worldperatio.com/major-stock-index-pe-ratios/ (check "Last Update") + the country table on the home page | Daily |
| valuation history: fpe, cape | G3, G5, exp. return | siblisresearch.com single-market pages: kospi-korea-pe-earnings, japan-nikkei-pe-cape, china-shanghai-pe-cape-ratio, dax-pe-ratio-yield, ftse-100-cape-pe-yield, france-pe-ratio-yield, canada-pe-earnings, hang-seng-cape, ibovespa-pe-ratio, cape-ratio-india-nifty; US and Australia CAPE from cape-ratios-by-country | Monthly |
| valuation history: dy | G7 | siblisresearch global-dividend-yields (country level; lags ~4 months) | Quarterly |
| cape_now, dy_now | exp. return (no-history markets) | siblis cape-ratios-by-country / global-dividend-yields snapshot | Monthly |
| pe_pct | G1 fallback | CSI 300: Dongwu weekly valuation PDF (pdf.dfcfw.com) | Weekly |
| fpe, fpe_avg10, y10, erp_avg10, rel_avg10 | G2, G4 (pilot 5) | FactSet Earnings Insight (S&P 500); siblis; **est.** norms | Monthly |
| policy_rate, policy_exp6m | M1, X3 | Trading Economics country-list/interest-rate; Fed: Kalshi/CME; ECB/BoJ: Reuters polls | Monthly |
| cpi, cpi_target, pmi | M4, M3 | Trading Economics country-list/inflation-rate and /manufacturing-pmi | Monthly |
| y10_chg6m | M2 | Pilot markets + India only (TE bonds page doesn't fetch) | Monthly |
| fx_inr_12m | X2 | ECB reference rates (today) vs x-rates.com historical (12 m ago) | Monthly |
| ret1y, ret3y | T4, F4 | MSCI factsheets (pilot markets) | Monthly |
| access, cost_pct (config) | exp. return net | **Estimates**; verify fund availability and the industry overseas-investment limit | Quarterly |

**Staleness:** flag any input older than its frequency as *(stale: date)* and estimates as *(est.)*.

## 4. How to read it

- Act on the **5-yr score band**. Use the **entry plan** for how fast to act.
- A cheap market with a falling price gets "enter in thirds", not "wait". A rich market with a rising price gets "trim into rallies".
- **Expected return** is a rough ranking aid, not a forecast. Compare it with Indian alternatives (10-yr G-sec ~7.2%).
- **Markets with one valuation input** (JCI, IPC, TASI, MOEX, RUT, AEX, WIG20, IBEX35, FTSEMIB, BIST100) are shrunk towards 50. Their true valuation extreme is in the §5b valuation log (`valuation_score`).
- **Earnings-cycle flags** matter most for Korea (memory boom: forward P/E −60% vs average but CAPE z +3.8), offshore China, Japan and Canada.

## 5. Output template

1. **Headline:** cheapest and richest markets (5-yr score → signal) and the data as-of date.
2. **Ranked table** (from `table`): market · 5-yr score · signal · entry timing · entry plan · expected INR return (net) · valuation (n indicators) · access. Nifty 50 is a row like the others.
3. **For each market asked about:** the top 3 pulls each way on the 5-yr score from `drivers` (value, score, Leading/Coincident/Lagging), plus the expected-return breakdown.
4. **Action list:** buy/accumulate (with plan) · hold · trim/exit.
5. **Data quality:** valuation indicators per market, cycle flags, proxies, estimates, stale inputs, access caveats.
6. **Caveat line:** single month, no back-test, judgment weights and growth assumptions, not investment advice.
7. **Files:** `global-indices-score-log.csv`.

Plain language, tables, explain jargon the first time, phone-readable.

### 5b. Valuation-only ranking

`python3 global_oscillator.py valuation` ranks all markets by the full Valuation bucket (cycle-adjusted). It shows pe_z10, cape_z, fwd-PE-vs-average and dy_z, plus the uniform G1 `valuation_score`, and writes `global-indices-valuation-log.csv`. Labels: ≤20 Very cheap · 21–35 Cheap · 36–50 Fair, cheap side · 51–65 Fair, rich side · 66–80 Expensive · >80 Very expensive. Always report the proxies, the estimated rows (Saudi Arabia, Russia), the Turkey inflation caveat and "not investable" (Russia).

## 6. Change log

- **21-Nov-2026: v1.0.** Implemented the improvement roadmap (plan §10):
  - #1/#6: index-specific valuation history file, with G3 (forward PE vs 10-yr average), G5 (CAPE z) and G7 (dividend-yield z) for 10–12 indices.
  - #3: 5-yr score + entry-timing score.
  - #8: staging rule; T4 now momentum.
  - #5: earnings-cycle check.
  - #4: expected INR return.
  - #9: access route and cost.
  - #7: measured norms replace estimates for G3 where history exists.
  - #10: monthly scheduled task.
  - Fixed a column-name clash (combined timing is now `entry_timing`).
- 20-Nov-2026 (21:30 IST): v0.4. Headline = absolute; Nifty 50 scored by this engine; no vs-Nifty column.
- 20-Nov-2026: v0.3 (all markets), v0.2 (valuation-only rows), v0.1 (5-index pilot).

## 7. What is still missing

- **Back-test (#2): blocked on data.** The free history is year-ends only (CAPE 2006–2025 for 10 markets; forward P/E 2016–2025) and has no total-return series. A proper test needs monthly prices and total returns: a market-data connector (Alpha Vantage, FactSet) or the paid Siblis database. Until then the weights, the 75/15/10 split and the growth assumptions are judgment.
- **Single-input valuation** for 13 markets (no free CAPE/forward-PE history for Spain, Italy, Netherlands, Mexico, Indonesia, Saudi Arabia, Poland, Turkey, Russia, Russell 2000, Nasdaq-100).
- **Not yet sourced:** G6 P/B, M2 for the new markets, M5, M6 modules, T2 outside the US, T5 RSI, T6 flows, F1 200-WMA, F3 ROE. X1 REER is an estimate (pilot only); G2/G4 norms are estimates (pilot only).
- **Proxies:** country ETFs for G1/T1 in most markets; SSE Composite for CSI 300 valuation history; Hang Seng for HSCEI; country-level dividend yields.
- TOPIX and FTSE 250 are not yet separate rows (no separate free history found).

## 8. Run log

| Run date | Month | Cheapest (5-yr) | Richest (5-yr) | Notes |
|---|---|---|---|---|
| 21-Nov-2026 (v1.0) | 2026-11 | HSCEI 28.8 Buy · Indonesia 29.3 Buy · Russia 30.0 (not investable) · Brazil 33.2 Buy · Mexico 33.6 Buy | Canada 85.0 Exit · Spain 75.4 · DAX 72.8 · Italy 72.5 · Turkey 70.2 · Poland 68.1 · Nikkei 67.5 · FTSE 100 66.9 (Trim) | Nifty 50 47.1 Accumulate (6 monthly tranches). S&P 500 63.0 Hold, exp. 4.0% INR. Highest exp. return: Indonesia 14.0, Brazil 11.9, HSCEI 11.2 |
| 20-Nov-2026 (v0.4, absolute) | 2026-11 | Indonesia 37.8 · offshore China 38.8 · Russia 40.0 · Mexico 40.6 · CSI 300 43.2 | Spain 70.3 · Italy 68.6 · Poland 68.5 · Germany 67.8 | Absolute blend, 24 rows incl. Nifty 50 59.8 |
| 20-Nov-2026 (v0.3, INR) | 2026-11 | Indonesia 35.3 · Russia 36.8 · Mexico 40.0 · Brazil 42.4 · offshore China 46.9 | Spain 69.1 · Italy 67.5 · Germany 66.5 | First full run on 23 rows |
| 20-Nov-2026 (valuation) | 2026-11 | Indonesia 1.0 · China offshore 2.2 · Russia 5.9 · Mexico 13.9 | Turkey 100 · Spain 100 · Italy 92.1 · Germany 88.6 | G1-only ranking |
| 20-Nov-2026 (pilot) | 2026-11 | CSI 300 50.6 Hold | DAX 66.5 Trim | First pilot run |

## 9. Learnings and pitfalls

1. worldperatio σ-deviations are on **country ETFs** (EWJ, EWG, FXI…), not the local index. Flag them as proxies. SPY/QQQ/IWM/VT are index proxies. The home page shows no "Last Update"; confirm freshness on the index page.
2. US CPI for Oct-2026 has **no YoY figure** (the 2025 shutdown left no base). Use the latest YoY (Sep 3.7%) until the Nov data on 10-Dec.
3. Japan's core CPI (2.1%) understates underlying inflation (BoJ-adjusted 3.2%), so M4 reads benign.
4. China: NBS and RatingDog PMIs diverge. Average them.
5. Put the **year in every search** and reject results dated in another year.
6. lixinger.com refuses fetches. Use the Dongwu weekly PDF for CSI 300 percentiles.
7. Saudi Arabia and Russia are not on worldperatio; their G1 z-scores are estimates.
8. Peripheral Europe and Poland are rich partly because of a bank-earnings regime change, not only froth.
9. **Thin valuation:** a single valuation input is shrunk half-way to 50. Show the §5b valuation score alongside.
10. Policy paths (M1) for the newer markets are estimated from each central bank's last move unless a forecast is cited. Re-check monthly.
11. The Trading Economics bonds page doesn't render via fetch, so M2 is blank outside the pilot markets and India.
12. **Earnings-cycle traps:** Korea's forward P/E (4.2x) is distorted by memory-chip peak earnings; CAPE z +3.8 is the honest reading. The cycle check halves G1/G3 automatically. Similar caution applies to Brazil (commodities) and Spain/Italy (banks).
13. siblis per-index pages list Oct-2026 plus year-ends 2016–2025 only. Nasdaq-100 and Russell 2000 publish current forward P/E and CAPE but no history, so they have no G3/G5 yet.
14. Valuation history is month-end (Oct-2026) while worldperatio is daily (19-Nov). Mixing them is acceptable for a 5-yr score; note the dates.
15. Column names: bucket columns (valuation, macro, currency, timing, filter) are separate from the combined `entry_timing`. Don't reuse bucket names for new outputs.

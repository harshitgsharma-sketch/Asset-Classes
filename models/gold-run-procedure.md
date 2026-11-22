# Gold Oscillator — Standard Run Procedure (follow on every gold query)

Applies whenever the user asks about gold: "today's score", "run the gold model", "gold update", "should I buy/sell gold", "gold trend/outlook". Goal: the **same method and the same output format every time**.

Project files (all under `claude/`):
| File | Role |
|---|---|
| `gold-valuation-model.md` | Model design, indicator table, fair value, entry/exit rules |
| `gold-run-procedure.md` | This playbook (conventions, sources, output template, change log) |
| `gold_oscillator.py` | Canonical engine — the only scoring code to use |
| `gold-inputs-monthly.csv` | Month-end indicator inputs, Jan-2018 → latest (i01..i30) |
| `gold-scenarios.json` | Fixed Bear/Base/Bull driver paths for the 5-yr projection |
| `gold-score-log.csv` | Generated monthly scores (history + every run) |
| Live Sheet | https://claude.ai/artifact/X8m8jbLnEHLoEe3GFCvhQd (Oscillator, Scorecard, Fair Value, Entry-Exit Rules, 5-Yr Scenarios, Sources) |

---

## 1. Steps

1. **Load** the six project files: `project_read` each. Write the script, CSVs and JSON into a working folder.
2. **Read the live Sheet** (Claude Docs connector, `readCells` on Oscillator A1:P42, Scorecard A1:K19, Fair Value A1:E21, 5-Yr Scenarios A1:J20). The Sheet is the source of truth for today's inputs and weights. If any weight or anchor in the Sheet differs from `SPEC` in the script, update `SPEC` and record it in §7.
3. **Refresh inputs.** For every indicator, check the age of its value. Refresh anything older than its update frequency (§3) with a web search, using the named source first. Record value, date and source.
4. **Write the current month's row** to `gold-inputs-monthly.csv` (month = YYYY-MM of the run date; overwrite if it exists; `source` = "live run DD-Mon-YYYY"). If a new month has started since the last row, finalise the previous month with month-end closes first.
5. **Run** `python3 gold_oscillator.py all` → score log, latest score + driver table, 5-yr projection, chart PNG.
6. **Cross-check:** script score vs Sheet `Oscillator!B4`. They must agree within ±1 when inputs are the same. If they don't, find the input that differs before reporting.
7. **Report** using the template in §5. Send the chart PNG and `gold-score-log.csv`.
8. **Save back** to the project (`project_write`, `local_path`): `gold-inputs-monthly.csv`, `gold-score-log.csv`, and `gold-scenarios.json` / script only if changed. Add a line to §8 (Run log) of this file.
9. **Offer** (don't do it unasked) to write refreshed inputs into the Sheet's input cells.

## 2. Fixed conventions (do not vary between runs)

- **Prices:** month-end closes (LBMA PM or spot close). "Today" = latest close.
- **ATH:** $5,589.38 intraday (28-Jan-2026) until broken. Distance from ATH uses the intraday high.
- **200-day MA ≈** mean of the last 10 month-end closes. **200-week MA ≈** mean of the last 46 month-end closes. Use the live 200-DMA/200-WMA if a reliable source gives it, and note which was used.
- **#2 Expected Fed change (bp, next ~6 m):** take it from fed funds futures / CME FedWatch (implied rate in ~6 m − current midpoint). If that's unavailable, use the proxy 0.55 × (2-yr yield − fed funds midpoint) × 100 and label it "proxy".
- **#3 CB buying:** latest WGC quarter that has been published (the quarter ends, then about a month's lag).
- **#5 Gold/CPI:** CPI-U NSA index of the latest published month.
- **#13 USD/INR:** % change vs same date 12 months earlier (RBI reference rate).
- **#16 CB reserve share:** WGC/ECB published figure. If none, estimate as 0.14×(G/1800)/(0.86+0.14×G/1800).
- **Units** as in `SPEC` (percent values entered as numbers, e.g. 5.6 not 0.056).
- **Weights** = Impact × Severity × Reliability × Stability from the Sheet. Blank inputs are skipped and weights are re-normalised within each bucket.
- **Score bands:** ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate slowly · 51–65 Hold · 66–80 Trim · >80 Exit. Veto: Filter ≥70 while Oscillator ≤35.
- **Scenarios:** use `gold-scenarios.json` unchanged. Exit prices are tied to the Sheet's 5-Yr Scenarios tab (Bear $2,848 / Base $4,482 / Bull $6,579, probabilities 25/50/25). Change them only when asked or when the Sheet changes, and log it in §7.

## 3. Data sources and update frequency

| # | Indicator | Source (first choice) | Freq |
|---|---|---|---|
| 1 | 10-yr real yield | FRED DFII10 | Monthly |
| 2 | Expected Fed change | CME FedWatch / fed funds futures | Monthly |
| 3 | CB buying | WGC Gold Demand Trends | Quarterly |
| 4 | DXY | ICE DXY close (Investing.com, usmacro) | Monthly |
| 5 | Gold/CPI | BLS CPI-U NSA | Monthly |
| 6 | ETF flows | WGC global ETF flows | Monthly |
| 7 | Gold/200-DMA | Live 200-DMA or 10-month proxy | Monthly |
| 8 | Term premium | FRED ACMTP10 (NY Fed ACM) | Monthly |
| 9 | CFTC managed money % OI | CFTC Disaggregated COT | Weekly→Monthly |
| 10 | Gold per $1T M2 | FRED M2SL | Monthly |
| 11 | Gold/AISC | WGC / Metals Focus AISC | Quarterly |
| 12 | Dow/Gold | Dow close | Monthly |
| 13 | USD/INR 12-m change | RBI reference rate / FRED EXINUS | Monthly |
| 14 | 10y−2y | FRED T10Y2Y | Monthly |
| 15 | China premium | Reuters "Asia Gold" weekly | Monthly |
| 16 | CB reserve share | WGC / ECB | Quarterly |
| 17 | Monthly RSI(14) | TradingView monthly (compute from closes if needed) | Monthly |
| 18 | GPR index | matteoiacoviello.com/gpr.htm | Monthly |
| 19 | Gold/200-WMA | Live 200-WMA or 46-month proxy | Monthly |
| 20 | CPI YoY | BLS | Monthly |
| 21 | Gold share of fin. assets | WGC / Incrementum "In Gold We Trust" | Annual |
| 22 | GVZ | FRED GVZCLS | Monthly |
| 23 | GDX/GLD 3-m change | GDX and GLD closes | Monthly |
| 24 | Distance from ATH | Spot vs $5,589.38 | Monthly |
| 25 | Z-score vs 3-yr trend | Optional (duplicates #7); leave blank | — |
| 26 | Hulbert sentiment | MarketWatch Hulbert columns | Monthly |
| 27 | Gold/silver | Spot closes | Monthly |
| 28 | Miners BPI | StockCharts $BPGDM | Monthly |
| 29 | JM Bullion F&G | jmbullion.com/fear-greed-index | Monthly |
| 30 | Gold/Brent | Brent close | Monthly |

**Staleness rule:** in the output, flag any input older than its frequency as *(stale: date)*. Flag any estimate as *(est.)*. State the data coverage %.

**Priority gaps to fill:** #17 RSI, #18 GPR, #23 GDX/GLD, #26 Hulbert, #28 BPI, #29 F&G, #21. History (2021–Oct 2026) also lacks #6, #9, #15 and #22, which are only filled from Nov 2026 on.

## 4. How to read the score (back-test notes, Nov-21 → Nov-26)

- History range: 36 (Dec-22) → 71 (Feb-26, Trim, at the ATH). It never reached Buy (≤35) or Exit (>80) in 5 years. σ ≈ 8.
- The Feb-26 Trim flag correctly marked the top. But mid-range readings (50–60) during the 2023–25 central-bank-driven bull run were followed by strong gains (in-sample corr. of score with next-12-m return ≈ +0.3). **Treat 50–65 as neutral, not bearish.** The model is reliable mainly at the extremes.
- Price-based indicators and macro indicators offset each other, so the score mean-reverts to ~45–58. A true Buy needs a price fall *and* easing at the same time (real yield ≤ ~2%, DXY < 100, Fed expectations ≤ 0).
- Pre-Nov-2026 history is reconstructed from approximate inputs (18 of 30 indicators). Treat it as indicative to ±3 points.

## 5. Output template (use every time, in this order)

1. **Headline (1–2 sentences):** score X/100 → SIGNAL, change vs last month, gold price (USD and ₹/10 g from the Sheet), data as-of date.
2. **Sub-scores table:** Valuation / Timing / Filter with weight and score, coverage %, and Sheet-vs-script check.
3. **Drivers:** the top 3 pushing towards sell and the top 3 pushing towards buy (from the script's driver table), each with value, score and a one-line reason.
4. **Trend:** yearly averages, 12-m average, 3-m slope, the high/low and where today sits, plus the chart PNG.
5. **What would change the signal:** concrete thresholds, e.g. real yield level, price vs fair-value Mid/Low, the CFTC level, and which entry tranche or exit rule from the Entry-Exit tab is closest to triggering.
6. **5-yr outlook table:** Bear/Base/Bull × probability × score path (Nov-27…Nov-31) × gold path, and the probability-weighted path, followed by 2–3 bullets of implications.
7. **Data quality:** stale/estimated/missing inputs and any convention used as a fallback (e.g. Fed proxy).
8. **Caveat line:** judgment-based anchors; not investment advice.
9. **Files:** chart PNG and `gold-score-log.csv`.

For a narrow question (e.g. "just today's score"), give items 1–3 and 7 and offer the rest.

## 6. Fair value and rules quick reference (from the Sheet)

- Fair value (blended M2 and AISC anchors): Low $2,425 · Mid $3,686 · High $5,470 (Nov-26 inputs; recompute from the Fair Value tab).
- Entry in thirds: Oscillator ≤35 → tranche 1; spot ≤ FV Mid → tranche 2; real yield ≤2.0% → tranche 3. Accelerate if CFTC ≤15% OI or spot ≤ FV Low × 1.1.
- Exit: composite worsens 2 reviews running; spot ≥ FV High; price/AISC ≥ 3.0×; CFTC ≥36% OI; 20% trailing stop once up ≥30%; time stop at entry + 57 months.

## 7. Change log (method / weights / scenarios)

- 19-Nov-2026: v1. SPEC copied from Sheet revision 7 (I×S×R×St). Scenarios aligned to the Sheet's exit prices. Nov-26 reproduced at 51.8 (Sheet 51.84).

## 8. Run log

| Run date | Month | Score | V / T / F | Signal | Gold $ | Coverage | Notes |
|---|---|---|---|---|---|---|---|
| 19-Nov-2026 | 2026-11 | 51.8 | 56.8 / 55.2 / 35.5 | HOLD | 3,875 | 88% | Baseline; history back-filled Nov-21→Oct-26 |

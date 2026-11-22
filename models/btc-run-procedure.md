# Bitcoin Oscillator — Standard Run Procedure (v1, 21-Nov-2026, indicative)

> **Release status:** v1. 15 indicators (13 live in Nov-2026), judgment anchors, history Nov-21 → Oct-26 reconstructed from prices plus the gold model's macro inputs, no out-of-sample back-test. Report it as **indicative**. It sizes a **small satellite** only (cap ≤5% of the investable portfolio); it is not a core-asset model.

Applies whenever the user asks about Bitcoin / BTC / crypto: "BTC score", "should I buy bitcoin", "bitcoin update", "crypto allocation", "how much bitcoin", "after-tax return on bitcoin", "VDA vs ETF". Goal: the **same method and the same output format every time**.

| File (`claude/`) | Role |
|---|---|
| `btc-model-design.md` | Design: indicators, anchors, tax layer, sizing rule, weaknesses |
| `btc-run-procedure.md` | This playbook |
| `btc_oscillator.py` | Canonical engine. The only scoring code to use |
| `btc-inputs-monthly.csv` | Month-end inputs, Jan-2018 → latest (closes from 2018; indicators from Nov-2021) |
| `btc-scenarios.json` | Bear/Base/Bull 5-yr paths, tax/cost assumptions, sizing rule |
| `btc-score-log.csv` | Generated monthly scores (history + every run) |

## 1. Steps

1. **Run order:** gold → Nifty 50 → sectors → global → asset classes → **Bitcoin**. BTC reuses the gold row's DXY, real yield, expected Fed change, M2 and USD/INR, so run gold first (or reuse its latest row and flag it *(stale: date)*).
2. **Load** the engine, inputs, scenarios and log (`project_read`; in Claude Code, use the files in `claude/`).
3. **Refresh inputs** (§3), putting the **year in every web search** and rejecting results dated in another year. Many crypto pages show a live ticker next to an older article: use the article's own dated figure, not the widget.
4. **Write the current month's row** (`month` = YYYY-MM; overwrite if it exists; `source` = "live run DD-Mon-YYYY" plus every value's date and source, "est." for judgment values). If a new month has started, finalise last month with its month-end close first.
5. **Run** `python3 btc_oscillator.py all` → score log, latest score + month-end range + drivers, 5-yr scenario paths, after-tax INR returns, position cap, chart PNG.
6. **Report** with the §5 template. Quote only numbers the script prints. Send `btc_oscillator_history_and_outlook.png` and `btc-score-log.csv`.
7. **Save back** inputs and score log (engine / scenarios only if changed) and add a §8 run-log line.

## 2. Fixed conventions

- **Prices:** BTC/USD month-end close (UTC). Mid-month, "today" = latest dated close/print; the headline is then a month-end prediction with the script's ±15% range.
- **ATH:** $126,198.07 intraday (6-Oct-2025) until broken; update `ATH_USD` in the engine and log it in §7.
- **Halvings:** 2016-07, 2020-05, 2024-04; next assumed 2028-04 (update when the block date firms up).
- **200-week MA / 200-day MA:** use a live dated value when available (`wma200_usd`, `dma200_usd`); otherwise the engine uses 46 / 7 month-end closes as proxies.
- **Realized price:** Glassnode / Axel Adler Jr / BGeometrics. MVRV is derived as price ÷ realized price, so both use the same date's price where possible. If only an MVRV value is published, put it straight into `i01`.
- **ETF flow (`i08`):** US spot BTC ETF net flow for the calendar month, $bn (Farside / SoSoValue). Mid-month = month to date. Treated **contrarian** (heavy outflows = capitulation = cheap).
- **Funding (`i07`):** 30-day average perpetual funding, annualised %, average of Binance/Bybit/OKX.
- **Shared inputs (identical to gold / Nifty same-month values):** DXY → `i12` (= gold `i04`), US 10-yr real yield → `i13` (= gold `i01`), expected Fed change → `i14` (= gold `i02`), `m2_tn` (gold), `usdinr` (gold/Nifty). Never re-source them separately.
- **Bands:** ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate slowly · 51–65 Hold · 66–80 Trim · >80 Exit. **Staging rule:** Filter ≥70 while Oscillator ≤35 → "BUY - STAGED (macro filter high)": buy in the tranche count from `sizing`, not a lump sum.
- **Tax layer:** VDA 30% + 4% cess (31.2%), 1% TDS on sales, no loss set-off or carry-forward (Budget 2026 unchanged). ETF-via-LRS comparison uses 12.5% LTCG with loss set-off. Change only when the law changes; log in §7.
- **Scenarios:** use `btc-scenarios.json` unchanged unless asked; log any change in §7.

## 3. Inputs and sources

| Col | Indicator | First source | Freq |
|---|---|---|---|
| btc_usd | Month-end close | CoinGecko / CoinMarketCap / statmuse monthly table | Monthly |
| realized_usd → i01 | MVRV | Glassnode, Axel Adler Jr realized-price chart, BGeometrics monthly report | Monthly |
| wma200_usd → i02 | Price / 200-WMA | Live 200-WMA (news, Bitstamp weekly closes) or 46-month proxy | Monthly |
| i03 | Distance from ATH | Price vs $126,198 | Auto |
| i04 | Halving-cycle phase heat | Auto from date | Auto |
| i05 | Puell multiple | CryptoQuant / LookIntoBitcoin | Monthly |
| dma200_usd → i06 | Mayer multiple | Live 200-DMA or 7-month proxy | Monthly |
| i07 | Funding 30-d annualised | CoinGlass / exchange data (news recaps) | Monthly |
| i08 | US spot ETF flow, month | Farside / SoSoValue / The Block weekly recap | Weekly→Monthly |
| i09 | Fear & Greed | alternative.me | Monthly |
| i10 | Monthly RSI(14) | Auto from closes | Auto |
| stable_bn → i11 | Stablecoin supply 3-m change | DefiLlama (StablecoinInsider weekly snapshot) | Monthly |
| i12–i15, usdinr, m2_tn | DXY, real yield, Fed, M2 YoY, USD/INR | Copy from the gold row | Monthly |

**Priority gaps:** `i05` Puell (last seen 0.74 in Jun-26, too stale to use), `i11` stablecoins (needs three monthly `stable_bn` values; first one 288.87bn on 16-Nov-26), MVRV history before Oct-26, ETF-flow / funding / F&G history before Nov-26.

## 4. How to read the score

- Reconstructed Nov-21 → Nov-26 (approx., ±5 points): high 80.6 (Mar-24), low 19.8 (Dec-22, the cycle bottom). In-sample correlation of the score with the next 12-month BTC return is −0.54 (n = 49): scores ≤35 were followed by a median +77%, scores ≥66 by a median −23%. This is **in-sample** and the anchors were set knowing that history, so treat it as a sanity check, not a back-test.
- Valuation (MVRV, 200-WMA, cycle phase) is the core for a 5-year holder. Timing tells you how washed-out the market is now. Filter is the dollar and liquidity regime: when it is ≥70 the cheap reading is real but the macro is still hostile, so stage entries.
- 5-year horizons from a cycle low tend to end in the *next* cycle's bear phase (Nov-31 ≈ 43 months after the 2028 halving). Selling on a Trim/Exit reading matters more for BTC than for any other model in this project.
- After-tax: VDA losses are dead losses. The model therefore sizes on the stress loss, not on the expected return.

## 5. Output template (use every time, in this order)

1. **Headline (1–2 sentences):** score X/100 → SIGNAL, change vs last month, BTC price in USD and ₹ lakh, data as-of date; mid-month, the month-end range.
2. **Sub-scores table:** Valuation 45% / Timing 35% / Filter 20% with scores, coverage %.
3. **Drivers:** top 3 towards sell and top 3 towards buy, each with value, score, Leading/Coincident/Lagging tag and a one-line reason.
4. **Trend:** yearly averages, 12-m average, 3-m slope, high/low, the last 12 months, chart PNG.
5. **What would change the signal:** e.g. MVRV < 1.0 (price below realized price), price back above the 200-WMA, Fed expectations ≤0, ETF flows turning positive.
6. **5-yr outlook:** Bear/Base/Bull × probability × score path × BTC path; prob-weighted path; then the **after-tax INR return table** (pre-tax, VDA net, ETF/LRS net, exit-on-signal) and the tax/cost drag.
7. **Position size:** the script's cap (VDA and ETF route), tranche plan, and the reminder that VDA losses cannot be set off.
8. **Data quality:** stale / estimated / missing inputs.
9. **Caveat line:** v1 indicative; judgment anchors; tax treatment to confirm with a CA; not investment advice.
10. **Files:** chart PNG and `btc-score-log.csv`.

For a narrow question ("just the score"), give items 1–3 and 8 and offer the rest.

## 6. Entry / exit rules (v1)

- **Entry:** Oscillator ≤35 → tranche 1; MVRV ≤1.0 or price ≤0.85× 200-WMA → tranche 2; Filter <60 (Fed on hold or cutting, real yield ≤2%) → tranche 3. Never exceed the script's cap.
- **Exit:** first Trim reading (≥66) → sell a third; ≥80 or MVRV ≥3.0 → sell another third; the rest on the first monthly close below the 200-DMA after an Exit reading. Every sale carries 1% TDS and 31.2% tax on the gain; a loss gives no tax relief.

## 7. Change log

- 21-Nov-2026: v1 built. 15 indicators, V45/T35/F20, staging rule, tax/cost layer, sizing rule. History reconstructed from monthly closes (digrin/statmuse) plus gold-model macro inputs.

## 8. Run log

| Run date | Month | Score | V / T / F | Signal | BTC $ | Coverage | Notes |
|---|---|---|---|---|---|---|---|
| 21-Nov-2026 | 2026-11 | 27.1 | 10.7 / 18.3 / 79.1 | BUY - STAGED (macro filter high) | 58,027 | 94% | v1 baseline, month in progress (range 23.5–31.9 at ±15%); Puell and stablecoin trend missing; ETF flow partial (est.) |

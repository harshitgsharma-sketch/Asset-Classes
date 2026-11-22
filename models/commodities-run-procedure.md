# Silver & Commodities Oscillator — Standard Run Procedure (v1, 21-Nov-2026)

> **Release status:** v1, **indicative**. Silver is a full model (17 indicators, reconstructed history from Nov-21, 5-yr scenarios). Brent crude and copper are tilt signals for MCX-futures-only exposures. Copper has one month of history. There's no out-of-sample back-test. Act only at the extremes (≤35 or ≥66).

Applies to: "silver score", "should I buy/sell silver", "silver ETF", "silver outlook", "gold vs silver", "gold/silver ratio", "crude oil / Brent score", "copper score", "MCX commodities", "commodity cycle". Design: `commodities-model-design.md`. For a **cross-asset** valuation ranking (silver vs bonds vs equity), use the asset-class model; this model gives silver its timing.

| File (`claude/`) | Role |
|---|---|
| `commodities-model-design.md` | Design, indicator tables, scenarios, weaknesses |
| `commodities-run-procedure.md` | This playbook |
| `commodities_oscillator.py` | Canonical engine. The only scoring code to use |
| `commodities-config.json` | Commodities, indicators, anchors, weights, ATHs (editable) |
| `commodities-inputs-monthly.csv` | One row per month-end of raw inputs (wide format) |
| `commodities-scenarios.json` | Silver Bear/Base/Bull 5-yr paths (tied to `gold-scenarios.json`) |
| `commodities-score-log.csv` | Output, regenerated every run |

## 1. Steps

1. **Run order:** gold → Nifty 50 → sectors → global → **commodities** → asset classes. This model copies gold's shared inputs and imports gold's Valuation bucket, so run gold first.
2. **Load** the engine, config, scenarios, inputs and log; write them to a working folder.
3. **Refresh inputs** (§3). Add or overwrite the run month's row (`month` = YYYY-MM). If a new month has started, first finalise the previous month with month-end closes. Record every value's date and source in `source`, and mark judgment values "est.".
4. **Run** `python3 commodities_oscillator.py all` (or `score SILVER`, `project`, `chart`). Quote only numbers the script prints.
5. **Report** with the §5 template. Send `commodities_oscillator_history_and_outlook.png` and `commodities-score-log.csv`.
6. **Save back** inputs and score log (engine, config and scenarios only if changed), and add a §7 run-log line.

## 2. Fixed conventions

- **Shared inputs, identical values:** `gold_usd`, `brent_usd`, `usdinr`, `cpi_index`, `dxy` (= gold i04), `tips10` (= gold i01), `fed_exp_bp` (= gold i02), `usdinr_12m` (= gold i13) are copied from the same month's row of `gold-inputs-monthly.csv`. `imp_gold_v` = gold-score-log `valuation`. Never refresh them separately here.
- **Silver price is owned by this model.** Use the latest close (month-end once the month is over). The gold and asset-class CSVs copy `silver_usd` from here on their next run (gold #27 GSR, asset-class silver row).
- **Prices:** month-end closes. Silver = spot (LBMA/COMEX), Brent = ICE front month, copper = LME 3-month ($/t).
- **ATHs** live in the config (silver $121.65 on 26/29-Jan-2026; copper ~$14,700 in Sep-2026, est.). Update them only when broken, and log the change in §6.
- **Price-derived indicators** (MA ratios, RSI, 12-m change, ATH distance, INR vs 36-m) are computed by the engine. Don't type them into the CSV.
- **CFTC:** legacy COT futures-only report, **non-commercial** (long − short) ÷ open interest × 100, latest Tuesday report. Silver code 084691, copper 085692.
- **Balances:** silver = Silver Institute / Metals Focus current-year forecast (Moz, deficit negative). Copper = ICSG current-year and next-year refined balance (kt, surplus positive).
- **Oil:** `brent_curve_m1m12` = front month minus 12th month ($/bbl, backwardation positive). `oil_stock_chg_mbd` = EIA STEO implied global stock change for the next two quarters (build positive).
- **Bands:** ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit. Veto: Filter ≥70 while Oscillator ≤35.
- **Scenarios:** use `commodities-scenarios.json` unchanged. If `gold-scenarios.json` changes, copy its gold paths and drivers here and log it in §6.

## 3. Inputs and sources

| Column | First source | Freq |
|---|---|---|
| silver_usd | Trading Economics / Kitco spot close | Monthly |
| copper_usd_t | LME 3-month (SMM, Fastmarkets, Trading Economics) | Monthly |
| shared gold columns | `gold-inputs-monthly.csv` same month | Monthly |
| pmi_global | J.P. Morgan Global Manufacturing PMI (S&P Global, ~1st business day) | Monthly |
| silver_cftc_net_pct, copper_cftc_net_pct | cftc.gov COT archive `deacmxsf<MMDDYY>.htm` (legacy futures-only, COMEX) | Weekly → monthly |
| silver_etf_flow_moz | Global silver ETP holdings change last month (Sprott monthly note, Metals Focus, Bloomberg) | Monthly |
| silver_balance_moz | Silver Institute World Silver Survey (April) and interim (November) | Twice a year |
| brent_curve_m1m12 | ICE Brent futures strip (barchart, CME, Reuters) | Monthly |
| oil_stock_chg_mbd | EIA STEO global inventory change table | Monthly (~10th) |
| copper_balance_kt, copper_balance_next_kt | ICSG forecast press release (April, October) | Twice a year |

**Staleness rule:** flag any input older than its frequency as *(stale: date)* and any estimate as *(est.)*, and state the coverage %.

## 4. How to read it

- **Silver** behaves like gold with roughly twice the beta. A low score after a crash (GSR > 90, price well below its 200-DMA) is the classic entry. It's vetoed only if the 200-WMA, balance and 12-m change also look rich.
- The silver score and the asset-class model's silver **valuation** row can differ: this one adds timing (Fed, DXY, positioning, momentum). Use the asset-class row for *what* is cheap, and this one for *when*.
- **Brent and copper** are futures-only for an INR investor. A low score suggests a tactical MCX or energy/miner-equity tilt, not a 5-yr hold. Roll yield and slab-rate tax are not modelled.
- Mid-range scores (36–65) are neutral. The models are most useful at the extremes.

## 5. Output template (use every time, in this order)

1. **Headline:** silver X/100 → SIGNAL, change vs last month, price in $/oz and ₹/kg at international parity (= $/oz × USD/INR × 32.1507), data as-of date. One line each for Brent and copper.
2. **Sub-scores table** (from `score`): commodity · price · oscillator · V / T / F · coverage · live · signal.
3. **Silver drivers:** the top 3 towards sell and the top 3 towards buy, with value, score, Leading/Coincident/Lagging and a one-line reason.
4. **Trend:** silver yearly averages, 12-m average, 3-m slope, high/low and the last 12 months, plus the chart PNG.
5. **What would change the signal:** concrete thresholds (GSR, price vs 200-DMA, real yield, Fed path, CFTC).
6. **Silver 5-yr outlook:** Bear/Base/Bull × probability × score path × price path, plus the probability-weighted path and exit price, and 2–3 bullets of implications.
7. **Brent and copper:** the top 2–3 drivers each, with access and cost caveats (MCX roll, LRS).
8. **Data quality:** stale, estimated and missing inputs, plus any shared input that differs from the gold CSV.
9. **Caveat line:** v1, indicative, judgment anchors, reconstructed history, not investment advice.
10. **Files:** chart PNG and score log.

For a narrow question ("just the silver score"), give items 1–3 and 8, and offer the rest.

## 6. Change log

- 21-Nov-2026: v1 built (roadmap item 5, "silver and commodities"). Silver 17 indicators, Brent 11, copper 11. History copied from `gold-inputs-monthly.csv` (silver from Nov-21; Brent scored from Nov-22, once 12-m change and RSI are available). Silver scenarios tied to the gold scenarios. OT4 (EIA stock change) direction set so that builds are a headwind (rich).

## 7. Run log

| Run date | Month | Silver | V / T / F | Signal | Silver $ | Brent | Copper | Notes |
|---|---|---|---|---|---|---|---|---|
| 21-Nov-2026 | 2026-11 | 34.5 | 28.2 / 42.8 / 26.8 | BUY | 42.0 | 57.2 HOLD | 61.0 HOLD (9/11) | First run. Silver −14.0 vs Oct. At the gold CSV's $47.1, silver would score 41.2 (Accumulate), so the Buy depends on the late-November price. Scenario prob-weighted path 35 → 47 → 47 → 49 → 50 → 49, exit ≈ $68.7 |

## 8. Learnings and pitfalls

1. Put the **year in every search**. Fortune and Trading Economics have identically named 2025 pages ("current price of silver 11-…-2025").
2. Silver fell from ~$48.5 (13-Nov) to below $42 (20-Nov) in one week. The gold CSV's 47.1 (19-Nov sheet) was already stale. The month-end close decides whether November is a Buy or an Accumulate (§7), so finalise Nov-26 with the 30-Nov close.
3. Indian silver ETF premium and discount figures are noisy: a 16-Nov-26 article showed Nippon Silver ETF at a "31% discount to iNAV", almost certainly a stale iNAV. Don't use them until a clean series exists.
4. Copper's record is reported as "above $14,700" (Sep-26). Replace it with the exact intraday high when it's sourced.
5. The silver back-test is in-sample and nearly all at mid-range scores. Its correlation with the next-12-month return is ≈0, so the model hasn't yet proven itself at the extremes.

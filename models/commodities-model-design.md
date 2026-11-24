# Silver & Commodities Entry/Exit Oscillator — Model Design (v1, indicative)

**Built:** 21 Nov 2026 · **Status:** v1, indicative. Silver is a full model (17 indicators, 5-yr history back-filled from Nov-21, scenarios). Brent crude (11 indicators, history from Nov-22) and copper (11 indicators, current month only) are indicative tilt signals.
**Objective:** score silver and the main commodities an INR investor can reach from 1 (cheap, tailwinds → buy) to 100 (rich, headwinds → sell) for a holding period of 5 years or less. Same engine, bands and conventions as the gold, Nifty, sector, global and asset-class models.

> **Every silver / commodity query: follow `claude/commodities-run-procedure.md`.** Score only with `claude/commodities_oscillator.py`. Inputs: `claude/commodities-inputs-monthly.csv`. Config: `claude/commodities-config.json`. Scenarios: `claude/commodities-scenarios.json`. Log: `claude/commodities-score-log.csv`.

> Not investment advice. Cheap/rich anchors and weights are judgment-based. Back-test: in-sample, reconstructed history only (§7).

## 1. Why these commodities

| Commodity | INR access | Holding-period fit | Status |
|---|---|---|---|
| **Silver** | Silver ETFs and FoFs (SEBI-allowed since 2022), MCX silver futures | Good: ETF can be held 5 yrs; taxed like gold ETFs | Full model |
| **Brent crude** | MCX crude futures only; overseas energy ETFs via LRS / international FoF | Poor for buy-and-hold (monthly roll, margin, slab-rate tax) | Indicative tilt / trading signal |
| **Copper** | MCX copper futures only; global copper-miner ETFs via LRS | Poor for buy-and-hold (roll, margin) | Indicative; needs price history |

Excluded in v1 (see config `excluded`): natural gas (seasonal, weather-driven), aluminium/zinc/nickel (thin retail liquidity on MCX), platinum/palladium (no Indian product), broad commodity indices (no INR product), agri (SEBI suspensions, policy-driven).

## 2. Method (identical to the other models)

- **Per-indicator score** = clamp(1 + 99 × (x − cheap) / (rich − cheap), 1, 100). High = rich or a headwind.
- **Weight** = Impact (1–5) × Severity (1–5) × Reliability (0.5–1.0) × Stability (0.5–1.0).
- **Buckets:** Valuation 35% · Timing 45% · Filter 20% (gold's split). Blank inputs are skipped and weights re-normalised inside each bucket. A bucket with one live indicator moves only half-way from 50 (`THIN_SHRINK` 0.5, as in the sector and asset-class models). A bucket with none drops out and the others re-normalise.
- **Minimum data:** a month is scored for a commodity only with ≥6 live indicators (`MIN_LIVE`).
- **Bands:** ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit. **Veto:** Filter ≥70 while Oscillator ≤35 → "BUY VETOED - wait".
- **Price-derived indicators** (computed by the engine from month-end closes, never typed in): price ÷ 10-month mean (≈200-DMA), price ÷ 46-month mean (≈200-WMA), monthly Wilder RSI(14), 12-month % change, distance from the all-time high, and silver's INR price vs its 36-month INR average.

## 3. Silver (17 indicators)

| ID | Indicator | Bucket | Lead/Lag | I | S | R | St | Cheap → Rich | Shared with |
|---|---|---|---|---|---|---|---|---|---|
| SV1 | Gold ÷ silver ratio | V | Leading | 5 | 4 | 0.875 | 1.0 | 95 → 55 | asset-class M3, gold #27 |
| SV2 | Silver ÷ US CPI × 100 (real price) | V | Leading | 4 | 4 | 0.875 | 1.0 | 5 → 22 | CPI = gold `cpi_index` |
| SV3 | INR price vs 36-m INR average | V | Leading | 3 | 3 | 0.75 | 1.0 | −15% → +60% | asset-class M2 |
| SV4 | Gold model Valuation bucket (import) | V | Leading | 3 | 3 | 0.75 | 1.0 | 1 → 100 | asset-class M1 |
| ST1 | US 10-yr real yield (TIPS) | T | Coincident | 4 | 4 | 0.875 | 0.75 | −0.5% → 3.0% | gold i01 |
| ST2 | Expected Fed change, next ~6 m | T | Leading | 4 | 4 | 0.875 | 1.0 | −100 → +75 bp | gold i02 |
| ST3 | DXY | T | Coincident | 3 | 4 | 0.875 | 1.0 | 90 → 110 | gold i04, Nifty |
| ST4 | USD/INR 12-m change | T | Coincident | 3 | 3 | 1.0 | 1.0 | +8% → −3% | gold i13 |
| ST5 | Silver ÷ 200-DMA (10-m proxy) | T | Leading at extremes | 4 | 5 | 1.0 | 1.0 | 0.75 → 1.40 | — |
| ST6 | Monthly RSI(14) | T | Leading at extremes | 2 | 4 | 0.75 | 1.0 | 30 → 85 | — |
| ST7 | COMEX non-commercial net long, % OI | T | Leading (contrarian) | 3 | 4 | 0.875 | 1.0 | 0 → 40 | — |
| ST8 | Global silver ETP flow, last month | T | Coincident | 3 | 3 | 0.75 | 0.75 | +30 → −30 Moz | — |
| ST9 | Distance from ATH ($121.65, Jan-26) | T | Coincident | 2 | 3 | 0.75 | 1.0 | −65% → 0% | — |
| ST10 | J.P. Morgan Global Manufacturing PMI | T | Leading | 3 | 3 | 0.75 | 0.75 | 54 → 47 | Brent, copper |
| SF1 | Silver ÷ 200-WMA (46-m proxy) | F | Lagging | 3 | 4 | 1.0 | 1.0 | 0.90 → 2.20 | — |
| SF2 | Market balance, current year (Silver Institute) | F | Lagging | 4 | 3 | 0.75 | 0.75 | −200 → +50 Moz | — |
| SF3 | 12-m price change (USD) | F | Lagging | 2 | 3 | 0.75 | 1.0 | −30% → +80% | — |

Silver is about half monetary metal and half industrial metal, so the Timing bucket mixes gold's macro drivers (real yield, Fed, DXY) with an industrial-demand gauge (PMI). The silver-specific anchors are wider than gold's because silver is about twice as volatile.

## 4. Brent crude (11 indicators)

| ID | Indicator | Bucket | Lead/Lag | Cheap → Rich |
|---|---|---|---|---|
| OV1 | Brent ÷ US CPI × 100 (real price) | V | Leading | 16 → 36 (≈$55 → $120 in Nov-26 dollars) |
| OV2 | Gold ÷ Brent (= gold i30) | V | Leading | 60 → 15 |
| OT1 | Brent ÷ 200-DMA (10-m proxy) | T | Leading at extremes | 0.75 → 1.30 |
| OT2 | Monthly RSI(14) | T | Leading at extremes | 30 → 80 |
| OT3 | 1st − 12th month spread (backwardation +) | T | Coincident | −5 → +12 $/bbl |
| OT4 | EIA STEO global stock change, next 2 qtrs | T | Leading | −1.5 (draw) → +2.0 (build) mb/d |
| OT5 | DXY | T | Coincident | 90 → 110 |
| OT6 | USD/INR 12-m change | T | Coincident | +8% → −3% |
| OT7 | Global Manufacturing PMI | T | Leading | 54 → 47 |
| OF1 | Brent ÷ 200-WMA (46-m proxy) | F | Lagging | 0.75 → 1.60 |
| OF2 | 12-m price change | F | Lagging | −40% → +60% |

## 5. Copper (11 indicators)

| ID | Indicator | Bucket | Lead/Lag | Cheap → Rich |
|---|---|---|---|---|
| CV1 | LME copper $/t ÷ US CPI (real price) | V | Leading | 20 → 45 |
| CV2 | Copper ($/lb) ÷ gold ($/oz) × 1000 | V | Leading | 1.2 → 3.0 |
| CT1 | COMEX non-commercial net long, % OI | T | Leading (contrarian) | −10 → 30 |
| CT2 | ICSG refined balance, next year | T | Leading | −400 (deficit) → +400 kt (surplus) |
| CT3 | Distance from ATH (~$14,700, Sep-26) | T | Coincident | −45% → 0% |
| CT4 | DXY | T | Coincident | 90 → 110 |
| CT5 | USD/INR 12-m change | T | Coincident | +8% → −3% |
| CT6 | Global Manufacturing PMI | T | Leading | 54 → 47 |
| CT7 | Copper ÷ 200-DMA (10-m proxy) | T | Leading at extremes | 0.80 → 1.30 (needs history) |
| CF1 | ICSG refined balance, current year | F | Lagging | −400 → +400 kt |
| CF2 | Copper ÷ 200-WMA (46-m proxy) | F | Lagging | 0.85 → 1.60 (needs history) |

## 6. Silver 5-yr scenarios (`commodities-scenarios.json`)

Gold price paths and macro drivers (real yield, Fed, DXY, USD/INR change) are copied from `gold-scenarios.json`, so the gold and silver outlooks can't contradict each other. Silver = gold path ÷ an assumed gold/silver-ratio path: Bear 88–85 (exit ≈ $33.5), Base 80 → 70 (≈ $64), Bull 72 → 58 (≈ $113). Probabilities 25/50/25, as for gold. The price-derived indicators are re-computed from the annual path (proxies). RSI and the INR-36-m measure are approximations in the projection.

## 7. Reading at build (21 Nov 2026, month in progress) and back-test notes

At build, silver scored **34.5 → BUY** (V 28.2 / T 42.8 / F 26.8, 17/17 inputs), on $42.0 (20-Nov). Brent scored **57.2 → HOLD**, and copper **61.0 → HOLD** (9/11 inputs). See the run log in the run procedure for the exact numbers.

- **Silver history** (Nov-21 → Oct-26) uses prices and macro inputs copied from `gold-inputs-monthly.csv` and gold's Valuation bucket from `gold-score-log.csv`, so it's reconstructed (±3 points). It ranges from 27.6 (Aug-22, ~$18) to 83.6 (Feb-26, Exit, near the top). In-sample, the score's correlation with the next-12-month return is about 0 (n = 49). Nearly all pre-2025 readings sat at 35–50 during a long bull run, so the model is untested at the extremes. The Feb-26 Exit reading was right, but it can't be scored yet because 12 months haven't passed.
- **Brent history** (Nov-22 → Oct-26) is price and FX only: no curve, EIA or PMI inputs. In-sample correlation with the next-12-month return is −0.82 (n = 37). It's flattered by mechanical mean reversion in the price-derived indicators, so don't treat it as evidence of skill.
- **Copper** has no price history in the project yet, so CT7 and CF2 are blank and the history is a single month.

## 8. Known weaknesses and next steps

1. Back-fill month-end silver (from 2010), LME copper and Brent curve histories. Then re-set the anchors to true 5th/95th percentiles and run a proper out-of-sample test.
2. Add an India-specific silver indicator: ETF premium or discount to iNAV, or the MCX-vs-landed-parity premium. In Oct-25 Indian silver ETFs traded at 5–12% premiums. A 16-Nov-26 report showed a 31% discount, which looks like a stale iNAV, so the data isn't reliable yet.
3. CFTC: v1 uses the legacy COT **non-commercial** net (% OI) because it's on the public weekly pages. Switch to disaggregated managed money once a clean series is sourced, as gold does.
4. Brent and copper are futures-only for INR investors. Roll yield (backwardation earns, contango costs), margin and slab-rate taxation aren't modelled. The tax-and-cost layer (roadmap item 3) should net these off.
5. Add a Valuation-bucket export for silver so the asset-class model can import it, as it does for gold.

## 9. Aluminium, zinc, iron ore and natural gas (added 24-Nov-2026, indicative)

Added as signals for Indian metal and energy stocks (NALCO, Hindalco, Vedanta, Hindustan Zinc, NMDC, Tata Steel, JSW Steel, ONGC, GAIL, fertilisers). None has an Indian ETF; MCX futures only.

- **Prices:** `models/commodity-prices-monthly.csv`, built by `scripts/fetch_commodity_history.py`. The base is World Bank Pink Sheet monthly averages (since 2000 here; the source goes back to 1960). The current month comes from Yahoo for aluminium (ALI=F), iron ore (TIO=F) and Henry Hub gas (NG=F). Zinc stays on the latest World Bank month, because Yahoo's COMEX zinc future barely trades: in two years its price changed on only 13 of 501 days.
- **Engine:** `history: true` in the config. `own_history()` computes derived series on the full history, then joins them to the input rows by month.
- **9 indicators each** (ids AL/ZN/FE/NG + V1–F2):

| Indicator | Bucket | Metals | Natural gas |
|---|---|---|---|
| Price percentile in its own 10-year record (nominal) | Valuation | 5 → 95 | 5 → 95 |
| Price vs its 10-year average | Valuation | −30% → +60% | −50% → +100% |
| Price ÷ 10-month MA | Timing | 0.80 → 1.30 | 0.60 → 1.60 |
| Monthly RSI(14) | Timing | 30 → 80 | 30 → 80 |
| DXY | Timing | 90 → 110 | 90 → 110 |
| USD/INR 12-month change | Timing | +8% → −3% | +8% → −3% |
| Global manufacturing PMI | Timing | 54 → 47 | 54 → 47 (lower weight) |
| Price ÷ 46-month MA | Filter | 0.85 → 1.60 | 0.60 → 2.00 |
| 12-month change | Filter | −30% → +60% | −50% → +100% |

- **Reading at build (Nov-2026; zinc Oct-2026):** iron ore 21.7 Buy, aluminium 42.9 Accumulate, natural gas 53.9 Hold, zinc 63.2 Hold.
- **Weaknesses:**
  - The valuation is nominal: no CPI deflator before 2021 in the project, so a long uptrend reads as "rich".
  - There are no supply/demand balances (ICSG, ILZSG, IAI) and no positioning data yet.
  - The World Bank figures are monthly averages, while the current month is a Yahoo close.
  - Not back-tested.

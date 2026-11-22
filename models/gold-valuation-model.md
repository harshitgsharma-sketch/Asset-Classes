# Gold Valuation Model — Entry/Exit Oscillator (≤ 5-year horizon)

**Live spreadsheet:** https://claude.ai/artifact/X8m8jbLnEHLoEe3GFCvhQd
**Built:** 19 Nov 2026 · **Status at build:** Oscillator 52 / 100 → HOLD (no fresh lump sums)
**Objective:** Score gold from 1 (undervalued → buy) to 100 (overvalued → sell) to time an entry and exit within a holding period of under 5 years. Investor base currency: INR (USD/INR included as a factor).

> **Every gold query: follow `claude/gold-run-procedure.md`** (steps, fixed conventions, sources, output template). Score with `claude/gold_oscillator.py` only. Inputs: `claude/gold-inputs-monthly.csv`. Scenarios: `claude/gold-scenarios.json`. History: `claude/gold-score-log.csv`.

> Not investment advice. Cheap/rich anchors and weights are judgment-based. Back-test: reconstructed history only (see §8).

---

## 1. Workbook structure

| Tab | Purpose |
|---|---|
| **Oscillator** (main) | 30 indicators in priority order → 1–100 score, sub-scores, signal |
| **Scorecard** | Original 11-factor −2…+2 scorecard; holds the monthly inputs the Oscillator links to |
| **Fair Value** | M2-multiple and AISC-multiple anchors → blended Low/Mid/High fair value |
| **Entry-Exit Rules** | Tranche entry rules, exit rules, trailing stop, 57-month time stop |
| **5-Yr Scenarios** | Bear/Base/Bull exit prices (USD and ₹/10 g), probability-weighted CAGR |
| **Sources** | Input values with sources and update frequency |

## 2. Oscillator method

- **Per-indicator score** = clamp(1 + 99 × (Current − Cheap end) / (Rich end − Cheap end), 1, 100). Cheap/rich ends ≈ historical 5th/95th-percentile levels (judgment).
- **Weight** = Impact (1–5) × Severity (1–5) × Reliability factor × Stability factor (High 1.0, Med-High 0.875, Medium 0.75, Low-Med 0.625, Low 0.5). The factors per indicator are in §3 and in `SPEC` in the script.
- **Three buckets** (blank inputs skipped, weight re-normalised):
  - Valuation — slow anchors — 35%
  - Timing — leading & coincident — 45%
  - Filter — lagging confirmers — 20%
- **Oscillator** = 0.35 × Valuation + 0.45 × Timing + 0.20 × Filter.
- **Signal bands:** ≤20 Strong buy · 21–35 Buy (add a tranche) · 36–50 Accumulate slowly · 51–65 Hold · 66–80 Trim · >80 Exit.
- **Veto:** if Filter sub-score ≥ 70 while Oscillator ≤ 35 → "Buy vetoed, wait".

## 3. Indicator list (priority order)

I = Impact, S = Severity, R = Reliability, St = Stability (from Sheet revision 7).

| # | Indicator | Role | Lead/Lag | I | S | R | St | Cheap→Rich | Value @ 19 Nov 2026 | Score |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | US 10-yr real yield (TIPS) | Timing | Coincident | 5 | 5 | 1.0 | 0.75 | −0.5% → 3.0% | 2.84% | 95 |
| 2 | Expected Fed change, next ~6 mo | Timing | Leading | 5 | 4 | 1.0 | 1.0 | −100 → +75 bp | +50 bp | 86 |
| 3 | Central-bank buying, last qtr | Filter | Lagging | 5 | 4 | 0.75 | 0.75 | 350 → 50 t | 321 t | 11 |
| 4 | Dollar index (DXY) | Timing | Coincident | 4 | 4 | 0.875 | 1.0 | 90 → 110 | 103.6 | 68 |
| 5 | Gold ÷ US CPI | Valuation | Leading (slow) | 4 | 4 | 1.0 | 1.0 | 3 → 16 | 11.7 | 67 |
| 6 | Gold ETF flow, last month | Timing | Coincident | 4 | 4 | 0.875 | 1.0 | +50 → −50 t | +19 t | 32 |
| 7 | Gold ÷ 200-day MA | Timing | Leading at extremes | 3 | 5 | 1.0 | 1.0 | 0.85 → 1.30 | ~0.89 (est.) | 10 |
| 8 | US 10-yr term premium | Valuation | Leading (slow) | 4 | 3 | 0.75 | 0.75 | 1.5% → −0.5% | 0.83% (stale) | 34 |
| 9 | CFTC managed-money net long (% OI) | Timing | Leading (contrarian) | 3 | 4 | 0.875 | 1.0 | 5 → 40 | 26% | 60 |
| 10 | Gold per $1T US M2 | Valuation | Leading (slow) | 3 | 3 | 0.75 | 0.75 | 85 → 250 | 166 | 49 |
| 11 | Gold ÷ AISC | Filter | Lagging | 3 | 3 | 0.75 | 1.0 | 1.2 → 3.2x | 2.0x | 41 |
| 12 | Dow ÷ Gold | Valuation | Leading (very slow) | 3 | 3 | 0.75 | 1.0 | 30 → 2 | ~13.3 (est.) | 60 |
| 13 | USD/INR 12-mo change | Timing | Coincident | 3 | 3 | 1.0 | 1.0 | +8% → −3% | +5.6% | 23 |
| 14 | US yield curve 10y−2y | Timing | Leading | 3 | 3 | 0.875 | 0.75 | −1.0 → +2.5 pp | +0.35 | 39 |
| 15 | China physical premium | Timing | Coincident→leading | 3 | 3 | 0.75 | 1.0 | +$20 → −$20 | +$5 (stale) | 38 |
| 16 | Gold share of CB reserves | Filter | Lagging | 4 | 2 | 0.75 | 1.0 | 10% → 35% | 27% | 68 |
| 17 | Monthly RSI | Timing | Coinc./leading at extremes | 2 | 4 | 0.75 | 1.0 | 30 → 85 | missing | — |
| 18 | Geopolitical Risk Index | Timing | Coincident | 2 | 4 | 0.625 | 0.75 | 60 → 250 | missing | — |
| 19 | Gold ÷ 200-week MA | Filter | Lagging | 2 | 4 | 1.0 | 1.0 | 0.95 → 1.8 | ~1.29 (est.) | 41 |
| 20 | US CPI YoY | Filter | Lagging | 3 | 2 | 0.5 | 0.5 | 6% → 0% | 3.7% | 39 |
| 21 | Gold share of global financial assets | Filter | Lagging | 3 | 2 | 0.625 | 0.75 | 1% → 6% | missing | — |
| 22 | Gold volatility (GVZ) | Timing | Coincident | 2 | 3 | 0.75 | 1.0 | 40 → 14 | ~27 (est.) | 51 |
| 23 | GDX/GLD 3-mo % change | Timing | Leading | 2 | 3 | 0.75 | 0.75 | +15% → −15% | missing | — |
| 24 | Distance from ATH ($5,589) | Timing | Coincident | 2 | 3 | 0.75 | 1.0 | −45% → 0% | −30.7% | 33 |
| 25 | Z-score vs 3-yr trend | Timing | Leading at extremes | 2 | 3 | 0.75 | 1.0 | −2 → +2.5 | missing (dup. of #7) | — |
| 26 | Hulbert Gold Newsletter Sentiment | Timing | Leading (contrarian) | 2 | 3 | 0.75 | 1.0 | −20 → 70 | missing | — |
| 27 | Gold ÷ silver | Timing | Coincident | 2 | 2 | 0.625 | 0.75 | 45 → 100 | 82.2 | 68 |
| 28 | Gold miners Bullish % Index | Timing | Leading (miners) | 1 | 3 | 0.5 | 0.75 | 5 → 95 | missing | — |
| 29 | JM Bullion Gold Fear & Greed | Timing | Coincident | 1 | 2 | 0.5 | 0.5 | 0 → 100 | missing | — |
| 30 | Gold ÷ Brent oil | Timing | Coincident | 1 | 2 | 0.5 | 0.5 | 10 → 60 | 42 | 65 |

## 4. Reading at build (19 Nov 2026)

- Gold spot ≈ $3,875/oz (≈ 31% below the 28 Jan 2026 ATH of $5,589)
- **Oscillator 52 → HOLD** · Valuation 57 · Timing 55 · Filter 36 · Data coverage 88%
- Bearish pull: real yields near 18-year highs, Fed hike cycle, strong dollar, gold/CPI elevated.
- Bullish pull: price stretched ~11% below 200-DMA, central-bank buying 321 t in Q3, rupee depreciation.
- Fair-value (Fair Value tab): blended Low $2,425 / Mid $3,686 / High $5,470 → spot ≈ 5% above Mid.
- 5-yr scenarios (Sheet): Bear $2,848 / Base $4,482 / Bull $6,579 (25/50/25) → weighted exit ≈ $4,598 → ≈ 3.5% CAGR USD, 6.2% INR.

## 5. Entry / exit rules (Entry-Exit Rules tab)

- **Entry in thirds:** composite turns positive / oscillator ≤ 35 → tranche 1; spot ≤ fair-value Mid → tranche 2; Fed pivot (real yield ≤ 2.0%) → tranche 3. Accelerate on washed-out CFTC positioning (≤ 15% OI) or spot ≤ fair-value Low × 1.1.
- **Exit:** composite deteriorates for 2 monthly reviews; spot ≥ fair-value High; price ÷ AISC ≥ 3.0x; CFTC ≥ 36% OI; 20% trailing stop once up ≥ 30%; hard time stop at entry + 57 months.

## 6. Maintenance

- Monthly run per `gold-run-procedure.md`: refresh inputs → add the month's row to `gold-inputs-monthly.csv` → run the script → save the log back to the project.
- Fill missing inputs: monthly RSI, GPR, Hulbert, GDX/GLD, miners BPI, JM F&G, gold share of global assets.
- India landed-cost markup set to 18% (15% import duty + 3% GST per Reuters, Oct 2026). Verify against current budget rules.

## 7. Open next steps

- Proper back-test: replace the reconstructed 2021–26 inputs with exact FRED/CFTC/WGC monthly series, and extend back to 2006 to test the 2011, 2020 and Jan-2026 tops. Then re-set the cheap/rich anchors to true percentiles.
- Consider dropping/merging redundant indicators (#25 into #7; #28 into #23).

## 8. Monthly back-fill Nov 2021 → Nov 2026 and 5-yr outlook (19 Nov 2026, full Sheet weights)

**Method:** 18 of 30 indicators reconstructed for each month-end, Nov-21 → Oct-26 (approximate inputs, ±3 pts). Nov-26 uses the live Sheet's inputs (22 indicators) and reproduces the Sheet exactly (51.8). Full data in `gold-inputs-monthly.csv`; scores in `gold-score-log.csv`.

**Yearly averages:** 2022 43 · 2023 40 · 2024 48 · 2025 56 · 2026 60. Range 36 (Dec-22, Accumulate) → 71 (Feb-26, Trim, at the ATH); σ ≈ 8.5. It never reached Buy (≤35) or Exit (>80).

**Findings:** the floor rose from 2022 to Feb-26 as the price outran the macro indicators. Since Feb-26 the score has rolled over (71 → 52, 3-m slope ≈ −3/month) as gold fell ~26%. Rising real yields and Fed hikes have stopped it falling into Accumulate. The Feb-26 Trim flag marked the top correctly. Mid-range readings (50–60) were followed by strong gains in 2023–25, so treat Hold as neutral.

**5-yr scenario projection** (`gold-scenarios.json`, exit prices = Sheet)
| Scenario | Prob | Score Nov-27 → Nov-31 | Gold path ($) |
|---|---|---|---|
| Bear | 25% | 49 → 45 → 43 → 42 → 41 | 3,300 → 3,000 → 2,900 → 2,850 → 2,848 |
| Base | 50% | 51 → 48 → 50 → 51 → 51 | 3,950 → 4,100 → 4,250 → 4,370 → 4,482 |
| Bull | 25% | 49 → 50 → 57 → 59 → 60 | 4,400 → 5,200 → 5,900 → 6,300 → 6,579 |
| Prob-weighted | | 50 → 48 → 50 → 51 → 51 | ≈ $4,598 exit |

Implication: the score most likely stays in a 41–60 band. A true Buy (≤35) needs a price fall *and* a Fed pivot together (real yield ≤ ~2%, DXY < 100). The likeliest window is 2027–28.

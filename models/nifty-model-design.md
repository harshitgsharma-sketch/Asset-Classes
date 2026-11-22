# Nifty 50 Entry/Exit Oscillator — Indicator Design (v2, BUILT)

**Status:** Built 19 Nov 2026. 40 indicators. Every Nifty query follows `claude/nifty-run-procedure.md` and is scored only with `claude/nifty_oscillator.py`, using the inputs in `claude/nifty-inputs-monthly.csv` and the scenarios in `claude/nifty-scenarios.json`. History is in `claude/nifty-score-log.csv`.
**Reading at build (Nov-26, month in progress):** Oscillator **51.3 → HOLD** · Valuation 47.1 · Timing 62.8 · Filter 36.8 · coverage 87%. Nifty 25,200 is 7.8% below fair-value Mid (27,320).
**Objective:** Score the Nifty 50 from 1 (cheap → buy) to 100 (rich → sell), to time entry and exit over a holding period of up to 5 years. Base currency is INR.

> Not investment advice. Cheap/rich anchors are judgment-based (roughly the 5th/95th percentiles since about 2010) and need to be reset from a real back-test.

---

## 1. Method (same engine as gold, two changes)

- **Per-indicator score** = clamp(1 + 99 × (Current − Cheap end) / (Rich end − Cheap end), 1, 100).
- **Weight W** = Impact (1–5) × Severity (1–5) × Reliability × Stability. Reliability and Stability are graded High 1.0 · Med-High 0.875 · Medium 0.75 · Low-Med 0.625 · Low 0.5.
- **Convention:** a high score means expensive, or a headwind for Indian equities. A low score means cheap, or a tailwind.
- **Buckets (change #1): Valuation 40% · Timing 40% · Filter 20%.** Gold uses 35/45/20. Valuation gets more weight here because starting PE and BEER are the best predictors of 3–5-year returns for Indian equities.
- **Signal bands:** ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit.
- **Veto (change #2, two rules):**
  1. *Falling knife:* Osc ≤35 with Filter ≥70, or 3-m EPS revisions ≤−3% → "Buy vetoed, wait".
  2. *Euphoria:* Osc ≥66, Nifty ÷ 200-DMA ≥1.12 and breadth ≥80% → Trim.

## 2. Full indicator list: 40 indicators ranked by weight (= priority)

I = Impact, S = Severity, R = Reliability, St = Stability, W = I×S×R×St. V/T/F = Valuation/Timing/Filter. Type: Leading = moves before the market; Coincident = moves with it; Lagging = confirms after the fact.

| Rank | Indicator | Type | Bucket | I | S | R | St | **W** | Cheap → Rich | Reading ~19 Nov 2026 | Score |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | BEER (10-yr G-sec ÷ Nifty earnings yield) | Leading | V | 5 | 4 | 1.0 | 1.0 | **20.0** | 1.0 → 1.9 | 1.48 | 54 |
| 2 | Nifty trailing PE | Leading | V | 5 | 5 | 1.0 | 0.75 | **18.8** | 14 → 28 | 20.6 | 48 |
| 3 | Expected RBI repo change, ~6 m | Leading | T | 5 | 4 | 0.875 | 1.0 | **17.5** | −75 → +75 bp | +25 (est.) | 67 |
| 4 | Nifty ÷ 200-day MA | Leading (at extremes) | T | 3 | 5 | 1.0 | 1.0 | **15.0** | 0.88 → 1.15 | 1.06 | 66 |
| 5 | 10-yr G-sec, 6-m change | Coincident | T | 4 | 4 | 0.875 | 1.0 | **14.0** | −75 → +75 bp | +20 bp | 64 |
| 6 | 12-m forward PE | Leading | V | 5 | 4 | 0.875 | 0.75 | **13.1** | 13 → 23 | 18.4 | 54 |
| 7 | EPS revisions, 3-m (FY+1) | Leading | T | 5 | 4 | 0.875 | 0.75 | **13.1** | +4% → −4% | +1% (est.) | 38 |
| 8 | India VIX | Coincident (contrarian) | T | 3 | 4 | 0.875 | 1.0 | **10.5** | 25 → 10 | 15.7 | 62 |
| 9 | % of Nifty 500 above 200-DMA | Leading (at extremes) | T | 3 | 4 | 0.875 | 1.0 | **10.5** | 15% → 85% | missing | — |
| 10 | FII net flow, 3 m | Coincident | T | 4 | 4 | 0.75 | 0.75 | **9.0** | −₹80k → +₹60k cr | +₹19k cr | 71 |
| 11 | Nifty ÷ 200-week MA | Lagging | F | 2 | 4 | 1.0 | 1.0 | **8.0** | 0.95 → 1.60 | 1.10 | 24 |
| 12 | Dollar index (DXY) | Coincident | T | 3 | 3 | 0.875 | 1.0 | **7.9** | 90 → 110 | 103.6 | 68 |
| 13 | Brent crude | Coincident | T | 4 | 3 | 0.75 | 0.75 | **6.8** | $55 → $110 | $93 | 69 |
| 14 | India–US 10-yr spread | Leading | T | 3 | 3 | 0.75 | 1.0 | **6.8** | 3.5 → 1.5 pp | 2.14 | 68 |
| 15 | FII ownership (Nifty 500) | Leading (slow, contrarian) | V | 3 | 3 | 0.75 | 1.0 | **6.8** | 15% → 23% | 17.1% | 27 |
| 16 | Midcap 150 PE ÷ Nifty PE | Leading (at extremes) | T | 3 | 3 | 0.75 | 1.0 | **6.8** | 0.9 → 1.8 | missing | — |
| 17 | India fwd-PE premium to MSCI EM | Leading (slow) | V | 3 | 3 | 0.75 | 1.0 | **6.8** | +15% → +100% | +40% (est.) | 30 |
| 18 | US high-yield credit spread | Leading | T | 3 | 3 | 0.75 | 1.0 | **6.8** | 6.0% → 2.5% | 3.20% | 80 |
| 19 | Monthly RSI(14) | Leading (at extremes) | T | 2 | 4 | 0.75 | 1.0 | **6.0** | 35 → 80 | 56.7 | 49 |
| 20 | India CPI YoY | Coincident | T | 3 | 3 | 0.875 | 0.75 | **5.9** | 2% → 7% | 6.09% | 82 |
| 21 | Market cap ÷ GDP | Leading (very slow) | V | 4 | 3 | 0.625 | 0.75 | **5.6** | 60% → 150% | ~130% | 78 |
| 22 | Shiller CAPE | Leading (5-yr) | V | 3 | 3 | 0.625 | 1.0 | **5.6** | 16 → 36 | missing | — |
| 23 | Nifty price-to-book | Leading (slow) | V | 3 | 3 | 0.75 | 0.75 | **5.1** | 2.2 → 4.2 | 2.95 | 38 |
| 24 | Equity MF net inflows, 3-m avg | Coincident | T | 3 | 3 | 0.75 | 0.75 | **5.1** | ₹8k → ₹45k cr | ₹27k cr | 52 |
| 25 | System liquidity (LAF % NDTL) | Leading | T | 3 | 3 | 0.75 | 0.75 | **5.1** | +1.5% → −1.0% | missing | — |
| 26 | Nifty EPS growth, TTM YoY | Lagging | F | 3 | 3 | 0.75 | 0.75 | **5.1** | +25% → −5% | +5.9% (TTM) | 64 |
| 27 | Real GDP growth | Lagging | F | 3 | 3 | 0.75 | 0.75 | **5.1** | 8.5% → 4.5% | 7.8% | 18 |
| 28 | Manufacturing PMI | Leading | T | 2 | 3 | 0.75 | 1.0 | **4.5** | 59 → 49 | ~55 (est.) | 41 |
| 29 | Nifty 3-yr CAGR | Lagging | F | 2 | 3 | 0.75 | 1.0 | **4.5** | 0% → 25% | 7.8% | 32 |
| 30 | Distance from ATH | Coincident | T | 2 | 3 | 0.75 | 1.0 | **4.5** | −30% → 0% | −4.4% | 85 |
| 31 | Rupee REER (40-ccy) | Leading (slow) | V | 2 | 3 | 0.75 | 1.0 | **4.5** | 90 → 108 | 92.8 (est.) | 16 |
| 32 | Primary issuance, 3 m | Leading | T | 3 | 3 | 0.625 | 0.75 | **4.2** | ₹15k → ₹90k cr | missing | — |
| 33 | MTF book YoY | Leading (froth) | T | 3 | 3 | 0.625 | 0.75 | **4.2** | −10% → +60% | ~+48% | 83 |
| 34 | Nifty dividend yield | Leading (slow) | V | 2 | 3 | 0.75 | 0.75 | **3.4** | 2.0% → 1.0% | 1.35% | 65 |
| 35 | Corporate profit ÷ GDP | Lagging | F | 3 | 2 | 0.625 | 0.75 | **2.8** | 2% → 6% | ~5% | 75 |
| 36 | Bank credit growth | Coincident | T | 2 | 3 | 0.625 | 0.75 | **2.8** | 18% → 8% | 18.1% | 1 |
| 37 | Promoter holding change, 4 qtrs | Lagging | F | 3 | 2 | 0.625 | 0.75 | **2.8** | +1.0 → −2.0 pp | +0.2 pp | 27 |
| 38 | Bank Nifty ÷ Nifty, 3-m | Leading | T | 2 | 3 | 0.625 | 0.75 | **2.8** | +6% → −6% | missing | — |
| 39 | Nifty put-call ratio | Coincident (contrarian) | T | 2 | 3 | 0.625 | 0.5 | **1.9** | 0.7 → 1.4 | missing | — |
| 40 | Nifty ÷ Gold (₹/10 g parity) | Leading (very slow) | V | 2 | 2 | 0.625 | 0.75 | **1.9** | 0.15 → 0.50 | 0.216 | 19 |

**Mix:** 24 Leading · 10 Coincident · 6 Lagging. **Bucket totals:** Valuation 91.4 (11) · Timing 171.5 (23) · Filter 28.2 (6). The exact current readings and scores come from the script's driver table; the values above are as of the build run.

### Why these ranks

- **BEER and trailing PE come first.** They have the best record for Indian 3–5-year returns, and BEER also captures the interest-rate regime. PE stability is 0.75 because NSE switched from standalone to consolidated EPS in Apr-2021.
- **The RBI path and G-sec momentum** are the main macro drivers, the counterparts to the Fed and real yields in the gold model.
- **EPS revisions get top-tier impact.** The 2025–26 drawdown was driven by about 9% EPS cuts, not by the multiple.
- **Flows are mid-weight** because they are noisy month to month. FII ownership is a slow contrarian anchor.
- **Market cap ÷ GDP is down-weighted** because it drifts structurally higher.
- **The v2 additions** (US HY spread, GDP, REER, MTF, dividend yield, credit, promoter holding, Bank Nifty relative return, PCR, Nifty ÷ Gold) add global risk appetite, leverage froth and cross-asset checks.
- **Excluded:** new demat accounts, GST collections and USD/INR 12-m change.

## 3. Build defaults (the open decisions, applied pending user review)

1. Buckets 40/40/20.
2. All 40 indicators kept. Prune after a deeper back-test.
3. Forward PE kept, at W 13.1.
4. FII 3-m flow weight 9.
5. The oscillator times lump sums only. Any SIP continues.
6. History back-filled 5 years (Nov-21 → Nov-26). A 20-year back-test (to include 2008) is an open next step.

## 4. Open next steps

- Fill the missing feeds: #9 breadth, #16 midcap/Nifty PE, #22 CAPE, #25 liquidity, #32 issuance, #38 Bank Nifty relative return, #39 PCR. Back-fill #6, #23 and #34.
- Extend the back-test to 2006 with exact NSE/RBI series, then reset the cheap/rich anchors to true percentiles.
- Optional: a live Sheet like the gold model's (Oscillator, Fair Value, Entry-Exit Rules, Scenarios tabs).
- Add a cross-asset layer: Nifty vs gold allocation, combining the two oscillators.

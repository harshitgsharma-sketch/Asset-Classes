# Bitcoin Entry/Exit Oscillator — Model Design (v1, 21-Nov-2026, indicative)

## 1. Purpose

A timing and sizing model for a **small Bitcoin satellite** in the portfolio of an INR investor with a holding period of 5 years or less. Same engine and bands as the gold and Nifty models (1 = cheap/buy, 100 = rich/sell). On top of the score it does two things the other models don't need to do:

1. **Tax-aware expected return.** India taxes VDA gains at a flat 30% + cess, deducts 1% TDS on every sale, and gives no relief for losses. That changes both the expected return and the right position size.
2. **A position-size cap**, so a cheap reading never turns into an outsized bet.

## 2. Engine

- Per-indicator score = clamp(1 + 99 × (x − cheap) / (rich − cheap), 1, 100).
- Weight = Impact × Severity × Reliability × Stability. Blank inputs are skipped and weights re-normalised within each bucket.
- **Oscillator = 0.45 Valuation + 0.35 Timing + 0.20 Filter.** Valuation carries more weight than in gold (0.35) because BTC's on-chain cost-basis measures have marked every cycle low and high, and the horizon is 5 years.
- **Staging rule** (replaces gold's veto): Filter ≥70 while Oscillator ≤35 → "BUY - STAGED". Hard vetoes would have kept an investor out at the 2022 low, when the Fed was hiking hardest.
- A month is scored once ≥6 indicators are present.

## 3. Indicators and anchors

| # | Indicator | Bucket | Type | I×S×R×St | Cheap → 1 | Rich → 100 | Why |
|---|---|---|---|---|---|---|---|
| 1 | MVRV (price / realized price) | V | Leading | 25.0 | 0.9 | 3.0 | Market price vs the average on-chain cost basis; <1 at every cycle low, >3 at tops (2.5–3 in recent cycles) |
| 2 | Price / 200-week MA | V | Leading | 20.0 | 0.85 | 2.5 | The 200-WMA has been the cycle floor; peaks have shrunk (≈2× in 2025) |
| 3 | Distance from ATH | V | Coincident | 14.0 | −75% | −5% | Past bear markets bottomed 77–84% below the high; shallower now |
| 4 | Halving-cycle phase heat | V | Leading | 6.75 | 1 | 100 | Months since halving: 50 at the halving, 100 at ~18 m (past tops), 1 at ~31 m (past lows), 50 again by 48 m |
| 5 | Puell multiple | V | Coincident | 5.06 | 0.5 | 3.0 | Miner revenue vs its 1-yr average; miner capitulation marks lows |
| 6 | Price / 200-day MA (Mayer) | T | Coincident | 16.0 | 0.7 | 1.6 | Trend stretch |
| 7 | Perp funding, 30-d annualised | T | Coincident | 10.5 | −5% | 25% | Leverage: longs paying >20–25% a year marks froth |
| 8 | US spot ETF net flow, month | T | Coincident | 9.0 | −$4bn | +$6bn | Contrarian: record redemptions mark capitulation |
| 9 | Crypto Fear & Greed | T | Coincident | 6.75 | 10 | 90 | Sentiment |
| 10 | Monthly RSI(14) | T | Lagging | 6.0 | 30 | 85 | Momentum stretch (computed from closes) |
| 11 | Stablecoin supply 3-m change | T | Leading | 5.06 | +10% | −5% | Crypto-native dry powder |
| 12 | DXY | F | Leading | 14.0 | 92 | 110 | Strong dollar = global liquidity squeeze (shared with gold/Nifty) |
| 13 | US 10-yr real yield | F | Leading | 12.0 | 0% | 3% | Opportunity cost of a zero-yield asset (shared with gold) |
| 14 | Expected Fed change, ~6 m | F | Leading | 16.0 | −100bp | +75bp | Policy direction (shared with gold) |
| 15 | US M2 YoY | F | Leading | 5.06 | 10% | 0% | Liquidity proxy (from the gold CSV's M2 series) |

All anchors are judgment-based, set from the 2018–2026 ranges. They should be re-tuned once a proper back-test exists.

## 4. Tax and cost layer (resident individual, FY2026-27)

| Item | VDA route (Indian exchange, spot BTC) | ETF route (US spot BTC ETF via LRS) |
|---|---|---|
| Tax on gain | 30% + 4% cess = **31.2%** (surcharge on top above ₹50 lakh income) | LTCG **12.5%** if held >24 months; slab rate if shorter |
| Loss | **No set-off, no carry-forward** | Set off against other capital gains |
| TDS / TCS | **1% TDS on every sale** (credited; refunded via ITR if a loss) | 20% TCS on LRS above ₹10 lakh/yr (credited) |
| Cost (model) | 1.5% round trip (fees + 18% GST + spread/INR premium, est.) | 0.5% a year (expense ratio + remittance/FX, est.) |
| Other | Exchange/custody risk; FIU-registered exchanges only | US estate-tax exposure above $60k; Schedule FA reporting; whether a BTC ETF is treated as a VDA is **not settled**, so confirm with a CA |

The engine applies these to each scenario's INR wealth multiple: gains are taxed, VDA losses are taken in full, and the delayed TDS refund on a losing sale costs the opportunity rate (7%) for one year.

**Nov-2026 result:** probability-weighted 5-yr return of 12.1% p.a. pre-tax becomes 8.7% on the VDA route (3.4 pp drag) and 10.4% on the ETF/LRS route (1.6 pp drag).

## 5. Position-size rule

Cap = min(band cap, loss budget ÷ stress drawdown).

- Band caps (% of investable portfolio): Strong buy 5 · Buy 4 · Accumulate 3 · Hold 2 (no new money above that) · Trim 1 · Exit 0. "BUY - STAGED" uses the Buy cap.
- Loss budget: 2% of the portfolio in a 60% fall from entry. On the VDA route that loss is fully unrelieved; on the ETF route it is shielded at the LTCG rate, so its cap is slightly higher.
- Build the position in 3 tranches (§6 of the run procedure). Buying on an Indian exchange carries no TDS; every sale does, which is a reason not to trade the position often.

## 6. Scenarios (btc-scenarios.json)

| | Prob | Nov-27 | Nov-28 | Nov-29 | Nov-30 | Nov-31 | INR depreciation |
|---|---|---|---|---|---|---|---|
| Bear | 25% | 42k | 50k | 68k | 52k | 45k | 3% p.a. |
| Base | 50% | 78k | 110k | 150k | 105k | 95k | 2% p.a. |
| Bull | 25% | 95k | 160k | 260k | 190k | 170k | 1% p.a. |

The paths follow a damped 4-year cycle: trough 2026-27, peak about 18 months after the April-2028 halving, then a bear phase into the end of the horizon. Realized price and 200-WMA paths are set to match. These are judgment paths, not forecasts.

## 7. Known weaknesses (v1)

- **No real back-test.** History is reconstructed from monthly closes and the gold model's macro inputs; MVRV, Puell, funding, ETF flows and sentiment have no history before Oct/Nov-2026. Most of the history rests on 8–9 of 15 indicators.
- **Anchors were set knowing 2018–2026**, so the in-sample fit (corr −0.54 with next-12-m return) is flattering.
- **Cycle dependence.** Indicator 4 and the scenarios assume the halving cycle keeps working. ETF and corporate-treasury ownership may be dampening it.
- **Tax treatment of foreign BTC ETFs** for Indian residents is not settled; the ETF column is a comparison, not advice.
- **Coverage gaps now:** Puell (#5) and stablecoin trend (#11). ETF flow for November is partial (est.).

## 8. Roadmap (v2)

1. Connect a data source for daily on-chain history (MVRV, realized price, Puell, STH cost basis) and back-test the bands properly.
2. Add STH cost basis, Coinbase premium and exchange reserves; consider a power-law fair-value band.
3. Add a regime input (VIX / HY spread) once the project's risk-regime detector exists.
4. Re-estimate band caps against the portfolio allocator once it is built.

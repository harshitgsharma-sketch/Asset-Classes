# Low-Risk Carry Model (arbitrage funds and Nifty covered calls) — Design (v1, indicative, built 21-Nov-2026)

**Goal:** when most assets score Hold, tell an INR investor whether low-risk carry is worth using right now, and which kind: an **arbitrage fund** (instead of a liquid fund) or a **covered call** on an existing Nifty holding. Holding period for parked money: 1–12 months; the covered call is an overlay on the core Nifty sleeve (5-year horizon, same as the Nifty model).
**Engine:** `carry_oscillator.py`. **Config:** `carry-config.json` (indicators, anchors, weights, tax scenarios, call strike/tenor). **Inputs:** `carry-inputs-monthly.csv`. **Log:** `carry-score-log.csv`. **Chart:** `carry-oscillator.png`. **Playbook:** `carry-run-procedure.md`.

> v1, indicative: one month of inputs, judgment anchors, no back-test, two estimated inputs. Not investment advice.

## 1. Principles

1. **Same scale as every other model, read as "how attractive is the carry".** 1 = carry very attractive (use it now), 100 = poor (stay in a liquid fund, or hold the Nifty uncapped). Standard bands: ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit. Each strategy also gets a plain action line (below).
2. **The hurdle is a liquid fund after tax.** Arbitrage only pays if it beats a liquid fund *after* tax, so the tax slab decides most of the answer.
3. **A covered call is not a bond.** It keeps the full Nifty downside less the premium and caps the upside every month. Its score says whether selling calls is well paid *now*; whether to own the Nifty at all stays with the Nifty model, which is imported (C4).
4. **Price the premium, don't scrape it.** The engine prices a 1-month ~2% out-of-the-money call with Black-Scholes from ATM implied vol (minus a call-skew allowance), so only market levels are needed.
5. **Reuse shared inputs:** Nifty level, India VIX (Nifty i08) and the Nifty oscillator come from the Nifty model; repo, expected repo path, expected CPI and the 91-day T-bill come from the asset-class inputs.

## 2. Engine

- Indicator score = clamp(1 + 99 × (x − attractive)/(unattractive − attractive), 1, 100). Config keys keep the project names `cheap` (= attractive end) and `rich`.
- Weight W = Impact × Severity × Reliability × Stability; blanks skipped and weights re-normalised; a strategy with one live indicator moves half-way to 50.
- Liquid hurdle = liquid-fund YTM − TER, taxed at slab.
- Arbitrage yield = the largest fund's 3-month direct-plan return, annualised (net of TER and of the 2026 STT hike, which the fund return already contains). Taxed as equity: STCG 20% + cess if held < 12 months (`arb_holding: short`), LTCG 12.5% otherwise.
- Covered call: premium % = BS call (vol = ATM IV − skew, 30 days, strike +2%, r = 91-d T-bill, q = Nifty dividend yield). Annualised = premium × 365/30 − cost (40 bp/yr est.: STT 0.15% on premium and on exercise, charges, slippage). Taxed at slab (individual's F&O premium is business income). Info columns: probability of being called away (risk-neutral N(d2)) and the loss in a 1-SD down month net of premium.
- Commands: `all`, `table`, `drivers`, `tax` (post-tax yields under each slab), `sens` (covered-call score vs India VIX 11–25), `chart`.

## 3. Indicators

| Strategy | Id | Indicator | Type | W | Attractive → poor |
|---|---|---|---|---|---|
| Arbitrage | A1 | Post-tax yield − post-tax liquid fund (pp) | Coincident | 21.9 | +1.5 → −0.25 |
| | A2 | Gross 3-m arbitrage return − liquid YTM (pp) | Coincident | 14.0 | +0.75 → −1.0 |
| | A3 | Latest 1-m arbitrage return, annualised − liquid YTM (pp) | Leading | 5.1 | +1.25 → −1.0 |
| | A4 | Gross 3-m arbitrage return − expected avg repo next 12 m (pp) | Leading | 6.8 | +1.75 → −0.25 |
| | A5 | Real post-tax yield vs expected CPI (pp) | Lagging | 10.5 | +2.0 → −2.0 |
| Covered call | C1 | Post-tax premium yield, annualised, net of cost (%) | Coincident | 21.9 | 14 → 4 (≈ VIX 24 → 11.5) |
| | C2 | India VIX level | Coincident | 16.0 | 22 → 11 |
| | C3 | Volatility risk premium: ATM IV − 20-d realised vol (pp) | Leading | 7.5 | +5 → −1 |
| | C4 | Regime fit: \|Nifty oscillator − 58\| (pts). Calls pay best in a range-bound Hold market; a cheap Nifty (Buy) should be held uncapped, a rich one (Trim/Exit) trimmed instead | Leading | 9.0 | 0 → 25 |
| | C5 | Premium cushion as % of a 1-SD monthly fall | Coincident | 6.8 | 30 → 5 |

**Action lines.** Arbitrage: ≤35 park idle and 3–12 m money in arbitrage · 36–50 prefer arbitrage over liquid for money parked ≥3 m · 51–65 either; liquid for <3 m · ≥66 prefer liquid/money-market. Covered call: ≤35 write calls on the whole core Nifty holding · 36–50 on about half · 51–65 small overlay only · ≥66 don't cap the upside.

## 4. Tax and cost assumptions (2026-27)

| Item | Treatment |
|---|---|
| Liquid / debt funds | Slab rate (no indexation, no LTCG) |
| Arbitrage funds | Equity-oriented: STCG 20%, LTCG 12.5% above ₹1.25 lakh a year (+4% cess) |
| Option premium written by an individual | Non-speculative business income at slab; ITR-3 and possibly audit thresholds |
| STT (from 1-Apr-2026, Budget 2026) | Futures 0.05% (was 0.02%), options 0.15% of premium / on exercise (was 0.10%/0.125%). Edelweiss MF estimated a 25–32 bp/yr drag on arbitrage funds |
| Scenarios in config | `slab30` (default, 31.2%), `slab20`, `slab10`, `nil`. Set `tax.scenario` to the user's slab |

Key consequence (Nov-2026): arbitrage beats a liquid fund only in the 30% slab (+0.66 pp); at 20% it is level and below that a liquid fund wins.

## 5. Known weaknesses (v1)

- One month, no back-test, anchors are judgment estimates from 2016–2026 ranges.
- **Realised vol (C3) and the Nifty dividend yield are estimates** until a measured 20-day realised-vol source is used (NSE historical index data).
- The arbitrage yield is one fund (Kotak, the largest) and lags by up to a month (factsheet date). A live Nifty next-month futures basis would be a better leading input.
- Black-Scholes with a flat skew allowance overstates premium when the call skew is steep; check against a quoted 2% OTM premium when one is at hand.
- Covered-call "yield" is the premium received, not the expected return: it gives back intrinsic value in months the call is exercised. Its true edge is the volatility risk premium (C3).
- Lot sizes (Nifty ~₹16–19 lakh notional) make the covered call impractical for small holdings; there is no plain covered-call MF in India today (some SIF hybrid long-short funds use it).

## 6. Roadmap

1. Back-fill 2018→ monthly: arbitrage category returns (AMFI), liquid category YTM, India VIX, Nifty realised vol, futures basis; reset anchors to percentiles and back-test "≤35 beats liquid after tax over the next 3 m".
2. Add the Nifty next-month futures annualised basis and market-wide arbitrage OI as leading inputs.
3. Add equity-savings funds and Bank Nifty covered calls; add a cash-secured put variant.
4. Feed the action line into the planned allocator / SIP engine for the "Hold everywhere" case.

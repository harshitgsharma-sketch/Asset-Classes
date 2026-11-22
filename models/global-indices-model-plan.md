# Global Indices (Top-20 Economies) Entry/Exit Oscillator — Design & Build Plan (v1.0, 21 Nov 2026)

> **Current state (21-Nov-2026): v1.0.** 23 markets + ACWI, Nifty 50 included. The headline is a 5-yr score plus an entry plan and an expected INR return. See §10 for the improvement roadmap and its status, and `global-indices-run-procedure.md` for how to run it. The sections below are the original design; where they differ, §10 and the run procedure are current.

**Status (20 Nov 2026):** Phase 1 pilot built and run: S&P 500, Nasdaq-100, CSI 300, Nikkei 225, DAX + MSCI ACWI. Run every query with `claude/global-indices-run-procedure.md` and score only with `claude/global_oscillator.py` + `claude/global-indices-config.json` + `claude/global-indices-inputs-monthly.csv`; results go to `claude/global-indices-score-log.csv`. The §9 defaults were applied at the user's instruction ("do the next steps as you deem feasible").
**First reading (2026-11):** CSI 300 50.6 Hold (relative 29.9 → overweight vs ACWI) · ACWI 55.3 · Nikkei 55.7 · S&P 500 57.3 · Nasdaq-100 59.6 · DAX 66.5 Trim. Nifty 50 51.3.
**Goal:** Score the main equity index(es) of the 20 largest economies from 1 (cheap, buy) to 100 (rich, sell) for an INR-based investor with a holding period of up to 5 years. Same engine and bands as gold, Nifty 50 and the sectors: ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit.
**Template:** the model is a clone of the sector model (`sector_oscillator.py`): own-history anchors, family bucket weights, an imported global block, and absolute + relative outputs.

> Not investment advice. Anchors are judgment-based until back-tested.

## 1. Universe: 20 economies, 25 indices

Country list from IMF WEO (Apr-2026, nominal USD GDP); re-check against the Oct-2026 WEO.

| # | Economy | Index(es) | Why more than one | Family |
|---|---|---|---|---|
| 1 | United States | S&P 500 · Nasdaq-100 · Russell 2000 | Core market / mega-cap tech & AI concentration / small caps, rate-sensitive | Developed |
| 2 | China | CSI 300 (onshore A) · Hang Seng China Enterprises (offshore H) | Different investor bases, valuations and access routes | Emerging |
| 3 | Germany | DAX | | Developed |
| 4 | Japan | Nikkei 225 · TOPIX | Price-weighted tech/export vs broad cap-weighted (banks, domestic) | Developed |
| 5 | United Kingdom | FTSE 100 · FTSE 250 | Global multinationals vs domestic economy | Developed |
| 6 | India | Nifty 50 (imported, not re-scored) | Home benchmark | — |
| 7 | France | CAC 40 | | Developed |
| 8 | Italy | FTSE MIB | | Developed |
| 9 | Russia | MOEX Russia | Score only; flag **Not investable** (sanctions, out of MSCI since 2022) | Emerging |
| 10 | Canada | S&P/TSX Composite | | Developed + commodity |
| 11 | Brazil | Ibovespa | | Emerging + commodity |
| 12 | Spain | IBEX 35 | | Developed |
| 13 | Mexico | S&P/BMV IPC | | Emerging |
| 14 | Australia | S&P/ASX 200 | | Developed + commodity |
| 15 | South Korea | KOSPI | | Emerging |
| 16 | Turkey | BIST 100 | Score in USD terms (high inflation distorts TRY PE) | Emerging (high-inflation rule) |
| 17 | Indonesia | Jakarta Composite | | Emerging + commodity |
| 18 | Netherlands | AEX | | Developed |
| 19 | Saudi Arabia | Tadawul All Share (TASI) | | Emerging + commodity (oil) |
| 20 | Poland | WIG20 | | Emerging |

Benchmark for relative scores: **MSCI ACWI**, which is scored as well as the "global market" row.

## 2. Design principles

1. **Anchors are each index's own history, never cross-country raw PE.** The US at 22x and the UK at 12x can both be fair. Cheap/rich = 5th/95th percentile, or −2σ/+2σ, of the index's own 10–20-yr monthly history.
2. **Three answers per index:**
   - **Absolute** (local currency): is this market cheap or rich vs its own past?
   - **Relative vs ACWI**: which countries to overweight/underweight.
   - **INR-adjusted** = Absolute + a Currency bucket: what an Indian investor actually earns, because returns arrive through the currency.
3. **Global macro is computed once** (US HY spread, VIX, DXY, Fed path, Brent), reusing gold/Nifty month-end values, and imported into each index as one indicator, like C4 in the sector model.
4. **"Abroad vs home" line:** each index's score sits next to the Nifty 50 oscillator, so the answer to "should I diversify out of India now?" falls out directly.

## 3. Engine

Same as the sector engine:
- Level: score = clamp(1 + 99 × (x − P5)/(P95 − P5), 1, 100)
- z-score: score = clamp(50 + 25 × (x − μ)/σ, 1, 100)
- W = Impact × Severity × Reliability × Stability. Blanks are skipped and weights re-normalised in each bucket. Thin-bucket rule: a bucket with one indicator moves only half-way to 50.

Five buckets: Valuation (V) · Macro & policy (M) · Currency (X, INR view only) · Timing (T) · Filter (F).

| Family | V | M | X | T | F |
|---|---|---|---|---|---|
| Developed | 40% | 20% | 10% | 20% | 10% |
| Emerging | 35% | 20% | 20% | 15% | 10% |
| Commodity-linked (overlay on either) | −5 V, +5 M (commodity module) | | | | |

The Absolute score drops X and re-weights. Relative uses only the Rel-tagged indicators.

## 4. Core indicators (every index)

| # | Indicator | Type | Bucket | W (draft) | Cheap → Rich | Rel |
|---|---|---|---|---|---|---|
| G1 | Trailing PE vs own 10-yr (σ) | Leading | V | 18.8 | −2σ → +2σ | |
| G2 | Equity risk premium: earnings yield − local 10-yr yield (BEER analogue) | Leading | V | 17.5 | Pctl (high ERP = cheap) | |
| G3 | 12-m forward PE pctl | Leading | V | 13.1 | Pctl | |
| G4 | Fwd PE ÷ ACWI fwd PE, z vs 10-yr | Leading | V | 14.0 | −2σ → +2σ | Rel |
| G5 | CAPE pctl (where published) | Leading (5-yr) | V | 10.5 | Pctl | |
| G6 | P/B pctl | Leading | V | 5.1 | Pctl | |
| G7 | Dividend yield pctl | Leading | V | 3.4 | Pctl (high = cheap) | |
| M1 | Expected policy-rate change, 6 m | Leading | M | 17.5 | −100 → +75 bp | |
| M2 | Local 10-yr yield, 6-m change | Coincident | M | 14.0 | −75 → +75 bp | |
| M3 | Manufacturing PMI | Leading | M | 6.0 | 58 → 47 | |
| M4 | CPI minus central-bank target | Coincident | M | 6.0 | −1 → +3 pp | |
| M5 | GDP consensus revision, 3 m (current + next yr) | Leading | M | 6.8 | +0.5 → −0.5 pp | |
| M6 | Country module (§5) | mixed | M | 6.8–10.5 | see §5 | |
| X1 | Currency REER vs 10-yr avg (BIS) | Leading (slow) | X | 10.5 | −10% → +10% | |
| X2 | Local ccy vs INR, 12-m change | Coincident (contrarian) | X | 6.8 | −10% → +15% | |
| X3 | Policy-rate gap vs RBI repo (carry) | Leading | X | 4.5 | +2 → −4 pp | |
| T1 | Index ÷ 200-DMA | Leading (extremes) | T | 15.0 | 0.88 → 1.15 (EM 0.85 → 1.20) | |
| T2 | EPS revisions, 3 m (FY+1) | Leading | T | 13.1 | +4% → −4% | |
| T3 | Global risk block (import: US HY spread, VIX, DXY, Fed path) | Leading | T | 14.0 | 1 → 100 as-is | |
| T4 | 6-m relative strength vs ACWI | Leading (contrarian) | T | 10.5 | −15% → +15% | Rel |
| T5 | Monthly RSI(14) | Leading (extremes) | T | 6.0 | 35 → 80 | |
| T6 | Foreign equity flows, 3 m (where published) | Coincident | T | 5.1 | Pctl | |
| F1 | Index ÷ 200-week MA | Lagging | F | 8.0 | 0.95 → 1.60 | |
| F2 | TTM EPS growth | Lagging | F | 5.1 | +20% → −5% | |
| F3 | ROE vs own 10-yr range | Lagging | F | 5.1 | Top → bottom | |
| F4 | 3-yr CAGR minus ACWI 3-yr CAGR | Lagging | F | 4.5 | −10 → +10 pp | Rel |

**The pilot implementation (engine `SPEC`) differs slightly:**
- G2 = ERP minus its 10-yr norm (+3 → −4 pp).
- G3 = forward PE vs its own 10-yr average (−25% → +25%).
- G4 = relative forward PE vs its 10-yr norm (−30% → +30%).
- M4 = absolute distance of CPI from target (0 → 3 pp).
- T3 = average of HY spread, DXY, Fed 6-m path and Brent (VIX not yet included).
- T4 uses the 1-yr USD return vs ACWI (−20 → +20 pp) until 6-m data is sourced.

The 10-yr norms are judgment estimates until back-filled (run procedure §7).

Design mix: 26 indicators — 18 Leading, 4 Coincident, 4 Lagging. Import weights: T3 Impact 5 for EM and Russell 2000; halved for Japan (the yen's safe-haven role offsets global risk).

## 5. Country / index modules (M6, 1–3 inputs each)

| Module | Applies to | Inputs |
|---|---|---|
| US | S&P 500, Nasdaq-100, Russell 2000 | Top-10 weight in index (concentration); Russell: share of floating-rate debt / HY spread |
| China | CSI 300, HSCEI | Credit impulse (TSF growth), property sales YoY, policy-stimulus score (1–5) |
| Japan | Nikkei, TOPIX | USD/JPY vs 5-yr range (exporter earnings), share of TOPIX below 1x P/B (governance reform runway) |
| Euro area | DAX, CAC, MIB, IBEX, AEX | ECB deposit-rate path, Euro-area PMI, BTP–Bund spread (MIB, IBEX) |
| UK | FTSE 100, FTSE 250 | GBP trade-weighted (FTSE 100 inverse), UK gilt 10-yr (FTSE 250) |
| Commodity | TSX, ASX, Ibovespa, TASI, JCI, MOEX | Relevant commodity vs 5-yr range (Brent, iron ore, copper, coal), China steel PMI |
| Tech-cycle | Nasdaq-100, KOSPI, AEX | Memory-chip prices / semiconductor billings YoY |
| High-inflation | BIST 100 | Real policy rate; score all valuation in USD terms |

## 6. Vetoes and flags

1. **Falling knife:** absolute ≤35 and (Filter ≥70 or EPS revisions ≤−3%) → "Buy vetoed, wait".
2. **Euphoria:** absolute ≥66 and index ÷ 200-DMA ≥1.15 (EM 1.20) → Trim.
3. **Value trap (commodity markets):** PE cheap while the commodity is in the top 20% of its 5-yr range → score on P/B and ERP only.
4. **Concentration:** top 3 stocks >30% of the index (Nasdaq-100, AEX/ASML, TASI/Aramco, KOSPI/Samsung + SK Hynix) → report and flag.
5. **Investability:** Russia → "Not investable"; China → policy-risk flag. Show the Indian access route for each index (NSE-listed ETF, international fund of funds, or LRS only), and flag when the industry overseas limit has halted fresh subscriptions.

## 7. Data plan (shell network is blocked: web fetch only, or a connector)

| Need | First source | Coverage / caveat |
|---|---|---|
| Country PE, σ vs 5/10/20-yr avg, % vs 200-DMA | worldperatio.com (country ETF proxies, e.g. VTI, FXI, EWG; index page has SPY, QQQ, IWM, VT) | 18 of 20 countries (no Saudi, Russia). **Verified fresh:** "Last Update 19 November 2026". Gives G1 and T1 with **no history back-fill needed** |
| PE, fwd PE, P/B, DY for all countries + ACWI | MSCI country index factsheets (monthly) | Uniform definitions; Russia discontinued |
| Index-specific PE (Nasdaq-100, Russell 2000, TOPIX, FTSE 250, CSI 300) | Index provider factsheets, siblisresearch, multpl (US); CSI 300: Dongwu weekly | Mixed definitions — note in the source column |
| CAPE | Barclays / Research Affiliates / siblis | Not all countries |
| Policy rates, 10-yr yields, CPI, PMI | Central banks, S&P Global PMI releases, Trading Economics news | Monthly |
| REER, FX | BIS REER; ECB reference rates crossed with USD/INR | Monthly |
| EPS revisions, fwd EPS | FactSet Earnings Insight (US); broker notes; connector | Weakest feed outside the US |
| Global block | Reuse gold/Nifty CSV values (DXY, Brent, US HY, USD/INR) | Identical month-end values |

**Connectors that would fill the biggest gaps:** Alpha Vantage (index prices → 200-DMA, 200-WMA, RSI, FX history) and FactSet (consensus EPS, forward PE, revisions). Without them, the pilot runs on 14–17 of 26 indicators.

## 8. Build phases

| Phase | Work | Output files (`claude/`) |
|---|---|---|
| 0 ✅ | §9 defaults applied 20-Nov-2026. Still to do: re-check the Oct-2026 WEO list | this file |
| 1 Pilot ✅ (20-Nov-2026) | 5 indices: S&P 500, Nasdaq-100, CSI 300, Nikkei 225, DAX (+ ACWI). `global_oscillator.py` cloned from `sector_oscillator.py`; config JSON; long-format inputs CSV; score log; run procedure | `global_oscillator.py`, `global-indices-config.json`, `global-indices-inputs-monthly.csv`, `global-indices-score-log.csv`, `global-indices-run-procedure.md` |
| 2 Full v1 (next) | Extend to all 25 in batches of 5 (next: Russell 2000, HSCEI, TOPIX, FTSE 100, FTSE 250); replace estimated norms with computed ones | updated config + inputs |
| 3 Back-test | Back-fill 20 yrs monthly (MSCI history, incl. 2008). Test: score ≤35 beats ACWI in INR over 12/36 m, ≥66 lags. Reset anchors to true percentiles; prune | updated design + config |
| 4 Cross-asset | Allocation view: gold vs Nifty vs global (one table using all oscillators) | `asset-allocation-view.md` |

Output template: see run procedure §5.

## 9. Decisions (defaults applied 20-Nov-2026; the user can still change them)

1. Universe: 25 indices as in §1. Poland (#20 by GDP) is in; Switzerland (#21, deeper, more investable) is an optional extra.
2. Russia: score-only with a "Not investable" flag.
3. Headline score: INR-adjusted (local-currency absolute shown alongside).
4. Relative benchmark: MSCI ACWI, with the Nifty 50 as a second column ("vs Nifty").
5. Data route: web fetch for now; Alpha Vantage / FactSet connectors suggested to fill the gaps.

## 10. Improvement roadmap (agreed 21-Nov-2026) and status

Order of implementation: 1 → 3 → 6 → 8 → 5 → 4 → 9 → 7 → 10; #2 last (needs data).

| # | Improvement | Status (21-Nov-2026) | What was done / what remains |
|---|---|---|---|
| 1 | 3–4 valuation inputs per market | **Partly done** | New `global-indices-valuation-history.csv` (siblisresearch). G3 forward PE vs 10-yr avg, G5 CAPE z and G7 dividend-yield z for 10–12 indices (S&P 500, Nikkei, DAX, FTSE 100, CAC 40, TSX, HSCEI*, CSI 300*, Ibovespa, KOSPI, Nifty 50, ASX 200). The other 13 still rely on G1 only: no free history found |
| 2 | Back-test, then set weights from results | **Blocked** | Free data is year-end only, with no total returns. Needs a market-data connector (Alpha Vantage / FactSet) or the paid Siblis database. Test: 5-yr score ≤35 beats ACWI in INR over 3–5 yrs; ≥66 lags |
| 3 | 5-yr score weighted to valuation + separate entry-timing score | **Done** | 5-yr = V 75 / F 15 / M 10; timing = T 60 / M 40. The v0.4 blend is kept as `blend_abs_v04` |
| 4 | Expected return in % | **Done (rough)** | Yield + real growth (DM 1.5 / EM 2.5) + half CAPE reversion + India inflation 4% − cost, ±3 pp. Markets without CAPE history get no reversion term; none for Turkey/Russia/ACWI |
| 5 | Earnings-cycle (value-trap) check | **Done** | Uses \|CAPE z − PE z\| ≥ 1. Flags and halves G1/G3. Triggered: KOSPI (+3.8), Nikkei, TSX, HSCEI (earnings above trend); CAC 40, ASX 200 (below trend). ROE (F3) still missing |
| 6 | Index's own data, not country-ETF proxies | **Partly done** | Valuation history is index-level (DAX, Nikkei, FTSE 100, CAC 40, TSX, KOSPI, Ibovespa, Nifty). G1/T1 still come from country ETFs. SSE stands in for CSI 300 and Hang Seng for HSCEI. TOPIX/FTSE 250 rows not added (no free history) |
| 7 | Replace estimated norms with measured ones | **Partly done** | G3 norms are now measured wherever history exists (the Nikkei, DAX and CSI 300 estimates were replaced). Still estimated: ERP and relative-PE norms (pilot), REER, M1 paths for the newer markets |
| 8 | Trend-aware timing + staging rule | **Done** | T4 is now momentum. Entry plan: price >15% below the 200-DMA → thirds over 6–12 m; tranche size set by the timing score |
| 9 | Access and cost layer | **Done (estimates)** | `access` and `cost_pct` in config; expected return is net of cost; Russia marked not investable. Verify fund availability and the overseas-limit status before acting |
| 10 | Automate data + keep monthly history | **Partly done** | Scheduled task "Asset Mgmt monthly model refresh" runs at 11:13 IST on the 3rd of each month (first run 3-Dec-2026). It refreshes all four models and appends to the logs and valuation history. A market-data connector would automate prices, 200-WMA, RSI and EPS revisions |

\* proxy index.

**Next:**
1. Connect a data source and run the back-test (#2).
2. Find CAPE/forward-PE history for Spain, Italy, Netherlands, Mexico, Indonesia, Saudi Arabia and Poland (e.g. MSCI factsheet archives).
3. Add ROE (F3) and P/B (G6).
4. After 6 months of logs, review signal stability.

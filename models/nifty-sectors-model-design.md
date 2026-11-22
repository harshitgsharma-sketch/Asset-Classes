# Nifty Sectoral / Size / Thematic Indices — Scoring Design (BUILT as v1, 20 Nov 2026)

**Status (20 Nov 2026):** v1 engine built and run for all 20 indices. Run every query with `claude/nifty-sectors-run-procedure.md` and score only with `claude/sector_oscillator.py` + `claude/nifty-sectors-config.json` + `claude/nifty-sectors-inputs-monthly.csv`; results in `claude/nifty-sectors-score-log.csv`. v1 implements 7 of the 17 core indicators plus C18–C20 and part of each module — see run procedure §7 for what differs from this design. The §6 anchors are superseded in v1 by own-history percentiles from indexpe.in.
**Editable doc:** https://claude.ai/artifact/JsKitKkpVfAGR9Fp6o39fX (design text; this file mirrors it).
**Benchmark:** Nifty 50 keeps its own 40-indicator model (`claude/nifty-model-design.md`).

> Not investment advice. Anchors are starting judgments and must be reset from back-tested data.

## 1. Purpose

Each index gets one score from 1 (cheap, buy) to 100 (rich, sell), on the same engine and bands as the Nifty 50 and gold oscillators: ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit.

Three changes from the Nifty 50 model:

- **Anchors are per index, from each index's own history.** FMCG at 45x and PSU Banks at 7x can both be fair. Cheap/rich ends = 5th/95th percentiles of the index's own 10-yr monthly history.
- **Two answers per index: absolute and relative (vs Nifty 50).** Allocation needs both.
- **A Sector cycle bucket is added** (4–6 sector-specific drivers). Macro is not rebuilt 20 times: the Nifty 50 model's Timing bucket score is imported as one input (C4).

Holding period ≤5 yrs, INR base, lump-sum timing only; SIPs continue regardless.

## 2. The 20 indices

Picked for visibility: index derivatives, ETF/index-fund assets, market coverage. NSE derivatives currently on Nifty 50, Bank, Financial Services, Midcap Select, Next 50, India FPI 150 (https://www.nseindia.com/products-services/about-equity-derivatives).

| # | Index | Family | Why in top 20 | Main valuation metric |
|---|---|---|---|---|
| 1 | Nifty Bank | Banks | F&O; largest sector ETF assets | P/B |
| 2 | Nifty Financial Services | Banks & financials | F&O | P/B |
| 3 | Nifty Next 50 | Size | F&O; large index-fund assets | PE |
| 4 | Nifty Midcap Select | Size | F&O (25 liquid midcaps) | PE |
| 5 | Nifty Midcap 150 | Size | Main midcap benchmark | PE |
| 6 | Nifty Smallcap 250 | Size | Main smallcap benchmark | PE (median) |
| 7 | Nifty 500 | Size | Whole-market benchmark | PE |
| 8 | Nifty Private Bank | Banks | ETFs; big index weight | P/B |
| 9 | Nifty PSU Bank | Banks | Heavily traded; high-beta cycle | P/B |
| 10 | Nifty IT | IT | Second-largest sector; ETFs | PE |
| 11 | Nifty Auto | Auto | Established ETFs | Forward PE |
| 12 | Nifty FMCG | Consumption | Defensive core | PE |
| 13 | Nifty Pharma | Healthcare | Defensive | PE |
| 14 | Nifty Metal | Commodities | High-beta cycle | P/B, EV/EBITDA |
| 15 | Nifty Energy | Commodities | Large weight | P/B |
| 16 | Nifty Realty | Rate-sensitive | High-beta cycle | P/B |
| 17 | Nifty CPSE | PSU theme | Government ETF | Dividend yield, PE |
| 18 | Nifty India Defence | PSU theme | Fast-growing ETFs since 2024 | PE |
| 19 | Nifty Infrastructure | Capex theme | Capex-cycle proxy | PE |
| 20 | Nifty India Consumption | Consumption | Thematic ETFs/funds | PE |

Left out: factor indices (Alpha 50, Midcap150 Momentum 50, Low Vol 30, Quality 30) — rule-based holdings make PE history non-comparable; score via their parent size index. **Update 21-Nov-2026:** factor indices now have their own v1 model — see `claude/nifty-factors-model-design.md`. India FPI 150: score like Nifty 100 until 3 yrs of history.

## 3. Engine

Per-indicator (level, percentile anchors):
score = clamp(1 + 99 × (x − P5) / (P95 − P5), 1, 100)

Relative measures (z-score vs 10-yr mean; −2σ → 1, +2σ → 100):
score = clamp(50 + 25 × (x − μ10y) / σ10y, 1, 100)

Swap ends where high is good. High score always = expensive / headwind.
Weight W = Impact × Severity × Reliability × Stability (grades as Nifty model). Missing inputs skipped, weights re-normalised within bucket. v1 adds a thin-bucket rule: a bucket with one indicator moves only half-way from 50.

Bucket weights by family:

| Family | Valuation | Sector cycle | Timing | Filter |
|---|---|---|---|---|
| Size (Next 50, Midcap, Smallcap, Nifty 500) | 40% | 15% | 30% | 15% |
| Defensives (FMCG, Pharma, Consumption) | 45% | 20% | 20% | 15% |
| Financials (Bank, Fin Services, Private Bank) | 35% | 30% | 20% | 15% |
| Deep cyclicals (PSU Bank, Metal, Energy, Realty, Auto) | 30% | 35% | 20% | 15% |
| Growth and themes (IT, Defence, CPSE, Infra) | 35% | 25% | 25% | 15% |

Two outputs per index: **Absolute** = four-bucket oscillator; **Relative** = same engine on the Rel indicators only (C3, C6, C8, C13, C16).

| | Relative ≤35 | Relative ≥66 |
|---|---|---|
| Absolute ≤35 | Strongest buy: add and overweight | Buy the market; prefer other sectors |
| Absolute ≥66 | Trim the market; this sector is the place to hold | Strongest sell: trim and underweight |

Vetoes:
1. Falling knife: absolute ≤35 and (Filter ≥70 or index 3-m EPS revisions ≤−3%) → "Buy vetoed, wait".
**Peak-earnings guard (built 22-Nov-2026, deep cyclicals):** when 5-yr EPS CAGR ≥ 20% and outruns price CAGR by ≥ 10 pp/yr (or Brent ≥ 80th pctl of its 5-yr range for Energy, or GNPA ≤ 3% for PSU Bank), P/E-based valuation indicators are floored at 50. See run procedure §6.
2. Euphoria: absolute ≥66, index ÷ 200-DMA ≥1.15 (≥1.20 mid/small) and % members above 200-DMA ≥85% → Trim.
3. Value trap (cyclicals): PE score ≤25 while operating margin in top 20% of history → drop PE, score on P/B or EV/EBITDA only.
4. Concentration: top 3 stocks >50% of index → check their own valuations; if >20 pts apart from index score, report both and flag.

## 4. Core indicators (every index)

Pctl = index's own 10-yr P5/P95. v1 live: C1, C3, C4, C8 (1-yr proxy), C12, C14 (5-yr proxy), C16 (5-yr proxy); plus C18 PE vs own 5-yr median, C19 5-yr re-rating, C20 Defence PE ÷ Nifty 500 PE.

| # | Indicator | Type | Bucket | I | S | R | St | W | Cheap → Rich | Rel |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | Primary valuation metric (PE or P/B per §2) | Leading | V | 5 | 5 | 1.0 | 0.75 | 18.8 | Pctl | |
| C2 | Index ÷ 200-day MA | Leading (extremes) | T | 3 | 5 | 1.0 | 1.0 | 15.0 | 0.85 → 1.15 (mid/small 0.80 → 1.25) | |
| C3 | Relative PE vs Nifty 50 (z vs 10-yr mean) | Leading | V | 4 | 4 | 0.875 | 1.0 | 14.0 | −2σ → +2σ | Rel |
| C4 | Nifty 50 model Timing bucket (macro import) | Leading | T | 4 | 4 | 0.875 | 1.0 | 14.0 | 1 → 100 as-is | |
| C5 | 12-m forward PE | Leading | V | 5 | 4 | 0.875 | 0.75 | 13.1 | Pctl | |
| C6 | Index EPS revisions, 3-m (FY+1) | Leading | T | 5 | 4 | 0.875 | 0.75 | 13.1 | +4% → −4% | Rel |
| C7 | Index BEER (10-yr G-sec ÷ earnings yield) | Leading | V | 4 | 3 | 0.875 | 1.0 | 10.5 | Pctl | |
| C8 | Relative strength vs Nifty 50, 6-m | Leading (contrarian) | T | 3 | 4 | 0.875 | 1.0 | 10.5 | −20% → +20% | Rel |
| C9 | % of members above 200-DMA | Leading (extremes) | T | 3 | 4 | 0.875 | 1.0 | 10.5 | 15% → 85% | |
| C10 | Index ÷ 200-week MA | Lagging | F | 2 | 4 | 1.0 | 1.0 | 8.0 | 0.95 → 1.60 (mid/small 0.90 → 1.80) | |
| C11 | Monthly RSI(14) | Leading (extremes) | T | 2 | 4 | 0.75 | 1.0 | 6.0 | 35 → 80 | |
| C12 | Secondary valuation metric (other of PE / P/B) | Leading | V | 3 | 3 | 0.75 | 0.75 | 5.1 | Pctl | |
| C13 | FII + MF sector weight vs 10-yr avg | Leading (contrarian) | T | 3 | 3 | 0.75 | 0.75 | 5.1 | −2σ → +2σ | Rel |
| C14 | TTM EPS growth | Lagging | F | 3 | 3 | 0.75 | 0.75 | 5.1 | +25% → −5% | |
| C15 | ROE vs own 10-yr range | Lagging | F | 3 | 3 | 0.75 | 0.75 | 5.1 | Top → bottom | |
| C16 | 3-yr CAGR minus Nifty 50 3-yr CAGR | Lagging | F | 2 | 3 | 0.75 | 1.0 | 4.5 | −10 pp → +10 pp | Rel |
| C17 | Dividend yield | Leading | V | 2 | 3 | 0.75 | 0.75 | 3.4 | Pctl (high yield = cheap) | |

Notes: C4 weight halved for FMCG, Pharma, Consumption; C4 Impact 5 for PSU Bank, Realty, Metal. C8 is contrarian over 3–5 yrs (momentum persists 1–3 m, so it sits in Timing). C1 + C5 together neutralise one-off earnings. C15 adjusts for quality.

## 5. Sector-cycle modules (Sector cycle bucket)

High = cycle near peak / turning against sector. The engine's live module inputs are listed in `SPEC` (S1–S3, B1–B4, I1–I2, K1–K4, A1, P1, M1–M2, R1–R2, G1–G2).

**5.1 Size (Next 50, Midcap 150, Midcap Select, Smallcap 250, Nifty 500)**

| Indicator | Type | W | Cheap → Rich | Source |
|---|---|---|---|---|
| Midcap (Smallcap) PE ÷ Nifty 50 PE | Leading | 13.1 | 0.9 → 1.8 (small 0.8 → 1.6) | niftyindices |
| Mid/small fwd EPS growth minus Nifty's | Leading | 10.5 | +10 pp → −5 pp | Consensus |
| Small/mid MF net inflows, 3-m avg | Coincident (froth) | 6.8 | Pctl | AMFI |
| IPO + SME issuance & listing gains, 3-m | Leading (froth) | 6.8 | Pctl | NSE, Prime Database |
| **S4 (built 22-Nov-2026):** sectoral/thematic MF froth: mean own-history pctl of 3-m net inflow ÷ equity AUM, share of equity net inflow, and 6-m rise in scheme count (NFO proxy). Also applied to CPSE, Defence, Infra. | Coincident (froth) | 5.1 | Pctl 0 → 100 | AMFI monthly report (automatic) |
| MTF book YoY | Leading (froth) | 5.1 | −10% → +60% | NSE/BSE |
| Advance–decline ratio, 3-m avg | Coincident | 4.5 | 0.7 → 1.6 | NSE |

Smallcap 250: median-stock PE or exclude loss-makers. Next 50: flag group/PSU concentration.

**5.2 Banks & financials (Bank, Fin Services, Private Bank, PSU Bank)**

| Indicator | Type | W | Cheap → Rich | Source |
|---|---|---|---|---|
| System credit growth YoY | Coincident | 13.1 | 8% → 18% | RBI |
| Credit minus deposit growth | Leading | 10.5 | −3 pp → +5 pp | RBI |
| GNPA direction, 4 qtrs | Lagging | 10.5 | Falling from peak → cycle low | RBI FSR, results |
| Expected repo change, 6-m | Leading | 9.0 | +50 bp → −75 bp | RBI, Nifty #3 |
| Sector NIM vs 5-yr range | Coincident | 6.8 | Bottom → top | Results |
| Credit cost | Lagging | 5.1 | Peak → trough | Results |

PSU Bank: P/B leads; stake sales / recaps as event flags. Fin Services: add AAA NBFC 3-yr spread over G-sec (wider = cheaper).

**5.3 IT**

| Indicator | Type | W | Cheap → Rich | Source |
|---|---|---|---|---|
| Top-5 cc revenue growth YoY | Coincident | 13.1 | Trough → peak | Results |
| Deal TCV book-to-bill | Leading | 10.5 | Pctl (high = cheap) | Results |
| US GDP + enterprise tech spend outlook | Leading | 9.0 | Accelerating → slowing | Gartner, IMF |
| USD/INR 12-m change | Coincident | 6.8 | Rupee −6% → +3% | RBI |
| Nifty IT PE ÷ Nasdaq-100 PE | Leading | 5.1 | Pctl | Bloomberg |
| Attrition | Lagging | 4.5 | Low → high | Results |

AI-disruption judgment flag: may require permanently lower PE anchors.

**5.4 Auto**

| Indicator | Type | W | Cheap → Rich | Source |
|---|---|---|---|---|
| Domestic volumes YoY (weighted PV/2W/CV/tractors) | Coincident | 13.1 | −10% → +20% | SIAM, FADA |
| Dealer inventory days | Leading | 9.0 | Low → high | FADA |
| Steel + aluminium, 6-m change | Leading | 6.8 | −15% → +20% | LME, JPC |
| Monsoon vs LPA | Leading | 5.1 | 105% → 90% | IMD |
| EBITDA margin vs 10-yr range | Lagging | 6.8 | Bottom → top | Results |

**5.5 Consumption (FMCG, India Consumption)**

| Indicator | Type | W | Cheap → Rich | Source |
|---|---|---|---|---|
| FMCG volume growth (rural/urban) | Coincident | 13.1 | Trough → peak | NielsenIQ |
| Food inflation | Coincident | 6.8 | 2% → 8% | MoSPI |
| Rural real wage growth | Leading | 6.8 | +4% → −1% | Labour Bureau |
| Palm oil + crude, 6-m change | Leading | 6.8 | −20% → +25% | Bloomberg |
| Monsoon vs LPA | Leading | 5.1 | 105% → 90% | IMD |

FMCG structurally high PE: rely on percentiles, never "rich because PE > Nifty".

**5.6 Pharma**

| Indicator | Type | W | Cheap → Rich | Source |
|---|---|---|---|---|
| US generics price erosion | Coincident | 10.5 | Low single digit → double digit | Results |
| USFDA warning letters + import alerts, 12-m | Leading | 9.0 | Few → many | USFDA |
| Domestic pharma market growth | Coincident | 6.8 | 12% → 5% | IQVIA, AIOCD |
| USD/INR 12-m change | Coincident | 5.1 | Rupee −6% → +3% | RBI |
| US pricing/tariff policy risk (1–5) | Leading | 5.1 | 1 → 5 | News |

**5.7 Commodities (Metal, Energy)**

| Indicator | Type | W | Cheap → Rich | Source |
|---|---|---|---|---|
| Fwd EV/EBITDA (Metal) or P/B (Energy) | Leading | 15.0 | Pctl | Broker, niftyindices |
| LME index or Brent vs 5-yr range | Coincident | 10.5 | Bottom → top | LME, ICE |
| China steel PMI + property starts | Leading | 9.0 | Recovering → overheating | NBS, Caixin |
| India steel spread or GRM | Coincident | 6.8 | Bottom → top | JPC, results |
| Govt pricing interference (1–5) | Leading | 5.1 | 1 → 5 | News |

Value-trap veto applies most here.

**5.8 Realty & Infrastructure**

| Indicator | Type | W | Cheap → Rich | Source |
|---|---|---|---|---|
| Housing sales YoY, top 7 cities (Realty) | Coincident | 10.5 | −15% → +25% | Anarock, PropEquity |
| Unsold inventory, months (Realty) | Leading | 10.5 | 30 → 12 | Anarock |
| Home loan rate vs 10-yr range (Realty) | Leading | 6.8 | Bottom → top | SBI, RBI |
| Central + state capex growth YoY (Infra) | Leading | 10.5 | +25% → −5% | CGA, Budget |
| Order book ÷ sales (Infra) | Leading | 6.8 | Pctl (high = cheap) | Results |

**5.9 PSU themes (CPSE, India Defence)**

| Indicator | Type | W | Cheap → Rich | Source |
|---|---|---|---|---|
| Dividend yield (CPSE) | Leading | 13.1 | Pctl (high = cheap) | niftyindices |
| Order book ÷ trailing sales (Defence) | Leading | 10.5 | Pctl (high = cheap) | Results |
| Defence capital budget growth YoY | Leading | 9.0 | +15% → 0% | Budget |
| Order inflow 12-m vs prior (Defence) | Coincident | 6.8 | +30% → −10% | Results |
| Stake-sale pipeline (1–5) | Leading | 5.1 | 1 → 5 | DIPAM |

Defence: short uptrending history (base Apr 2018). v1 implements the guard as C20 = Defence PE ÷ Nifty 500 PE (1.0 → 2.0).

## 6. Per-index set-up (design anchors — superseded in v1 by own-history percentiles)

| # | Index | C1 metric | Approx. cheap → rich | Module | Special rule |
|---|---|---|---|---|---|
| 1 | Nifty Bank | P/B | 1.8 → 3.3 | 5.2 | Concentration check |
| 2 | Nifty Financial Services | P/B | 2.3 → 4.5 | 5.2 | NBFC spread |
| 3 | Nifty Next 50 | PE | 18 → 35 | 5.1 | Group/PSU concentration |
| 4 | Nifty Midcap Select | PE | 20 → 45 | 5.1 | Euphoria at 200-DMA ≥1.20 |
| 5 | Nifty Midcap 150 | PE | 20 → 45 | 5.1 | Euphoria at 200-DMA ≥1.20 |
| 6 | Nifty Smallcap 250 | Median PE | 18 → 40 | 5.1 | Exclude loss-makers |
| 7 | Nifty 500 | PE | 17 → 28 | 5.1 | Cross-check vs Nifty 50 |
| 8 | Nifty Private Bank | P/B | 1.9 → 3.8 | 5.2 | Concentration check |
| 9 | Nifty PSU Bank | P/B | 0.4 → 1.6 | 5.2 | Value trap; C4 Impact 5 |
| 10 | Nifty IT | PE | 18 → 35 | 5.3 | AI-disruption flag |
| 11 | Nifty Auto | Fwd PE | 15 → 30 | 5.4 | Value trap on margin peaks |
| 12 | Nifty FMCG | PE | 38 → 55 | 5.5 | C4 halved |
| 13 | Nifty Pharma | PE | 24 → 42 | 5.6 | C4 halved |
| 14 | Nifty Metal | EV/EBITDA, then P/B | 4 → 9 (P/B 0.8 → 2.5) | 5.7 | Value trap; never lead with PE |
| 15 | Nifty Energy | P/B | 1.2 → 2.6 | 5.7 | Concentration; value trap |
| 16 | Nifty Realty | P/B | 1.2 → 5.0 | 5.8 | C4 Impact 5 |
| 17 | Nifty CPSE | Div yield | 7% → 2.5% | 5.9 | DY leads, PE second |
| 18 | Nifty India Defence | PE | 25 → 70 | 5.9 | Capped rich anchor |
| 19 | Nifty Infrastructure | PE | 15 → 30 | 5.8 | Capex module |
| 20 | Nifty India Consumption | PE | 35 → 60 | 5.5 | C4 halved |

NSE PE switched standalone → consolidated in Apr 2021: splice or start percentiles from 2021 where the jump is large.

## 7. Run, data, pitfalls

See `claude/nifty-sectors-run-procedure.md` (steps, sources, output template, run log, learnings).

Pitfalls: cyclical PE inverts at earnings peaks; Mar/Sep reconstitution shifts PE; short histories (Defence) bias anchors; concentration (Bank Nifty, Energy); structural re-rating (FMCG); mid-range scores are noise — act at ≤35 / ≥66.

## 8. Open next steps

- [x] Build `sector_oscillator.py` + `nifty-sectors-config.json` (v1, 20-Nov-2026).
- [x] Write `nifty-sectors-run-procedure.md`; inputs CSV and score log created.
- [ ] Back-fill 10 yrs monthly PE/PB/DY for all 20 (needs a data route to niftyindices.com history).
- [ ] Add the missing core indicators (C2, C5, C6, C7, C9, C10, C11, C13, C15, C17).
- [ ] Back-test: score ≤35 beats Nifty 50 over 12/36 m? ≥66 lags?
- [ ] Prune non-contributing indicators; fix weights.
- [ ] Sector-rotation view: all 20 on one absolute-vs-relative chart.

# Nifty Factor / Smart-Beta Indices — Rotation Model Design (v1, indicative, 21 Nov 2026)

**Status:** v1 built and run for 10 NSE factor indices that have index funds or ETFs. Run every query with `claude/nifty-factors-run-procedure.md` and score only with `claude/factor_oscillator.py` + `claude/nifty-factors-config.json` + `claude/nifty-factors-inputs-monthly.csv` + `claude/nifty-factors-sector-weights.csv`. Results go to `claude/nifty-factors-score-log.csv`. One month of scores, no back-test: **indicative only**.

> Not investment advice. Anchors are starting judgments and must be reset from back-tested data.

## 1. Purpose

Answer two questions for an INR investor with a holding period of 5 years or less:

1. **Absolute:** is this factor index cheap or rich right now (deploy cash or not)?
2. **Relative / rotation:** versus the Nifty 50, which factor sleeve should be overweighted and which underweighted?

Same engine and bands as every other model in the project: 1 = cheap/buy, 100 = rich/sell. ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit.

The sector design (§2) left factor indices out because their holdings rotate, so their PE history mixes different baskets. v1 handles this in three ways:
- It leans on **measured own-history percentiles and PE vs 5-yr median**, which compare like-for-like rule sets even if the names change.
- It adds a **sector look-through**: the index's current sector mix is scored with the sector model, so the valuation of what it holds *today* counts.
- It gives the Valuation bucket a lower weight for momentum indices (30%), where the basket changes most.

## 2. The 10 indices (all have index funds or ETFs)

| Key | Index | Family | Parent universe | Beta (Oct-26) |
|---|---|---|---|---|
| MOM30 | Nifty200 Momentum 30 | Momentum | Nifty 200 | 1.15 |
| MIDMOM50 | Nifty Midcap150 Momentum 50 | Momentum | Midcap 150 | 1.11 |
| ALPHA50 | Nifty Alpha 50 | Momentum (high-alpha) | Top 300 | 1.12 |
| ALPHALV30 | Nifty Alpha Low-Volatility 30 | Low-vol (multi-factor) | Nifty 200 | 0.89 |
| LOWVOL30 | Nifty100 Low Volatility 30 | Low-vol | Nifty 100 | 0.86 |
| QUAL30 | Nifty200 Quality 30 | Quality | Nifty 200 | 0.86 |
| MIDQUAL50 | Nifty Midcap150 Quality 50 | Quality | Midcap 150 | 0.96 |
| VALUE20 | Nifty50 Value 20 | Value | Nifty 50 | 0.85 |
| VALUE50 | Nifty500 Value 50 | Value | Nifty 500 | 0.92 |
| EQWT50 | Nifty50 Equal Weight | Equal weight (size tilt) | Nifty 50 | 0.98 |

Left out in v1: Nifty200 Value 30 (P/E history only from Jun-2024), Nifty500 Momentum 50 and the multi-factor MQVLv indices (too few funds/too short), Nifty Dividend Opportunities 50.

## 3. Engine

- Per indicator: score = clamp(1 + 99 × (x − cheap)/(rich − cheap), 1, 100). High = expensive / headwind.
- Weight W = Impact × Severity × Reliability × Stability. Missing inputs are skipped and weights re-normalised within the bucket. Thin-bucket rule: a bucket with one live indicator moves only half-way from 50.
- **C4 macro import × beta:** the Nifty 50 model's Timing bucket is imported as in the sector model, but its weight is multiplied by the index's beta. High-beta momentum sleeves carry more market-timing risk than low-vol sleeves.

Bucket weights by family (V / X / T / F):

| Family | Valuation | Factor cycle | Timing | Filter |
|---|---|---|---|---|
| Momentum (MOM30, MIDMOM50, ALPHA50) | 30% | 20% | 35% | 15% |
| Low-vol (ALPHALV30, LOWVOL30) | 40% | 20% | 25% | 15% |
| Quality (QUAL30, MIDQUAL50) | 45% | 15% | 25% | 15% |
| Value (VALUE20, VALUE50) | 40% | 20% | 25% | 15% |
| Equal weight (EQWT50) | 40% | 15% | 30% | 15% |

**Relative** = the same engine run on the Rel indicators only (C3, X2, C8, C16). Quadrants are as in the sector model: both ≤35 → strongest buy; both ≥66 → strongest sell; relative ≤35 → overweight; relative ≥66 → underweight.

**Rotation read:** rank the factor indices by relative score. The lowest are the sleeves to tilt towards, the highest the ones to tilt away from. Act only when a score is at an extreme (≤35 or ≥66).

## 4. Indicators (v1, all live)

| # | Indicator | Type | Bucket | I | S | R | St | W | Cheap → Rich | Rel |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 | PB percentile vs own 5-yr history | Leading | V | 5 | 5 | 0.875 | 0.75 | 16.4 | 0 → 100 | |
| C12 | PE percentile, estimated from indexpe.in zone label | Leading | V | 3 | 3 | 0.625 | 0.75 | 4.2 | 0 → 100 | |
| C18 | PE vs own 5-yr median | Leading | V | 5 | 4 | 0.875 | 0.75 | 13.1 | −35% → +35% | |
| C3 | Relative PE vs Nifty 50, vs 5-yr norm ("factor spread") | Leading | V | 4 | 4 | 0.875 | 1.0 | 14.0 | −30% → +30% | Rel |
| X1 | Sector look-through: Σ sector weight × sector-model absolute | Leading | X | 4 | 3 | 0.75 | 0.75 | 6.8 | 1 → 100 | |
| X2 | Sector look-through: Σ sector weight × sector-model relative | Leading | X | 4 | 3 | 0.75 | 0.75 | 6.8 | 1 → 100 | Rel |
| X3 | India VIX regime fit | Coincident | X | 2 | 3 | 0.625 | 0.75 | 2.8 | 11 → 25 (momentum, low-vol, quality); 25 → 11 (value, equal weight) | |
| C4 | Nifty 50 model Timing bucket, weight × beta | Leading | T | 4 | 4 | 0.875 | 1.0 | 14 × β | 1 → 100 | |
| C8 | 1-yr total return minus Nifty 50 | Leading (contrarian) | T | 3 | 4 | 0.875 | 1.0 | 10.5 | −25 pp → +25 pp | Rel |
| C14 | EPS CAGR, 5-yr | Lagging | F | 3 | 3 | 0.625 | 0.75 | 4.2 | +25% → −5% | |
| C16 | 3-yr CAGR minus Nifty 50 3-yr CAGR | Lagging | F | 2 | 3 | 0.75 | 1.0 | 4.5 | −10 pp → +10 pp | Rel |
| C19 | 5-yr re-rating: price CAGR − EPS CAGR | Lagging | F | 3 | 3 | 0.75 | 1.0 | 6.8 | −10 pp → +10 pp | |

Notes:
- **C3 is the factor-timing signal with the best evidence:** a factor's valuation spread against the market, versus its own norm, predicts multi-year relative returns (Asness et al., Arnott et al.). For Value it is the classic value spread.
- **C8 is contrarian** over 3–5 years, as in the sector model. Factor momentum persists for 1–12 months, so it sits in Timing, not Valuation. A 12-month horizon user should read it the other way.
- **X3 direction:** high VIX goes with momentum crashes (sharp reversals) and with low-vol/quality having already outperformed, so it is a headwind for those. For value and equal weight, high fear tends to be a better entry. This is a judgment anchor with low weight.
- **X1/X2 overlap:** the sector scores already include C4, so X1 double-counts a little of the macro import. The weight is kept low.
- **C14 has a lower reliability (0.625)** than in the sector model, because "EPS growth" of a rotating basket is partly an artefact of the rebalancing.

Vetoes and flags:
1. Falling knife: absolute ≤35 and Filter ≥70 → "Buy vetoed, wait".
2. Momentum crash watch: momentum family and India VIX ≥22 → flag.
3. Value re-rating: value family and C19 ≥ +5 pp → "value spread may have closed".
4. Concentration and data-quality flags come from the config.

## 5. Roadmap (v2+)

- **Back-test**: monthly PE/PB/DY and TRI history from niftyindices.com for each factor and the Nifty 50, then 12/36/60-m forward relative returns by score band. Reset anchors from that.
- **Measured PE percentile** to replace the zone-label estimate (C12).
- **Factor dispersion / crowding**: PE of the top quintile vs the bottom quintile of the parent universe; ETF/index-fund AUM flows per factor.
- **Momentum-specific**: rebalance turnover and market-reversal indicator (Nifty 1-m return after a ≥15% drawdown).
- **Look-through for EQWT50**: equal weights by sector from the constituent list.
- **Rebalance and SIP engine** (coordinator item 4): turn the rotation ranks into sleeve weights.

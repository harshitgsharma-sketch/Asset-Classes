# Nifty Factor / Smart-Beta Indices — Standard Run Procedure (v1, indicative — published 21-Nov-2026)

> **Release status:** v1 is indicative. One month of scores (Nov-26), judgment anchors, no back-test. All 12 v1 indicators are live for 9 of 10 indices (EQWT50 lacks the sector look-through). C12 is an estimate from a zone label. Quote the `indicators` column and the v1 status every time.

Applies to any question about NSE factor / smart-beta indices: "momentum vs quality", "is low-vol cheap", "which factor fund", "factor rotation", "smart beta", "equal weight vs Nifty", "value index". Same method and same output every time. Design rationale: `nifty-factors-model-design.md`.

Project files (all under `claude/`):
| File | Role |
|---|---|
| `nifty-factors-model-design.md` | Design: indices, buckets, indicators, roadmap |
| `nifty-factors-run-procedure.md` | This playbook |
| `factor_oscillator.py` | Canonical engine. The only scoring code to use |
| `nifty-factors-config.json` | Per-index set-up: family, bucket set, beta, VIX direction, flags; NSE sector → sector-model map |
| `nifty-factors-inputs-monthly.csv` | Long format, one row per (month, index). Raw inputs |
| `nifty-factors-sector-weights.csv` | Long format, (month, index, sector, weight). Factsheet sector mix for the look-through |
| `nifty-sectors-score-log.csv` | **Imported** from the sector model (X1/X2) |
| `nifty-factors-score-log.csv` | Generated scores (regenerated every run) |

## 1. Steps

1. **Run the Nifty 50 model, then the sector model first.** C4 = Nifty `timing` (put it on the NIFTY50 row as `nifty_timing`), X3 = Nifty input i08 India VIX (`vix` on the NIFTY50 row), X1/X2 read `nifty-sectors-score-log.csv`.
2. **Load** engine, config, inputs, sector weights and both logs; write them to a working folder.
3. **Refresh inputs** (§3). Add rows for the new month (`month` = YYYY-MM of the run). Put the date and source in `source`.
4. **Run** `python3 factor_oscillator.py all` (or `... drivers MOM30 QUAL30`). Quote only numbers the script prints.
5. **Report** with the §5 template. Send `nifty-factors-score-log.csv`.
6. **Save back** inputs, sector weights, score log (engine/config only if changed). Add a §8 run-log line.

## 2. Fixed conventions

- **Score:** clamp(1 + 99 × (x − cheap)/(rich − cheap), 1, 100). High = expensive/headwind. Bands ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit.
- **Weights:** W = I × S × R × St (`SPEC` in the engine). Blanks skipped, weights re-normalised inside each bucket; a missing bucket drops out.
- **Buckets** (V / X Factor cycle / T / F): momentum 30/20/35/15 · low-vol 40/20/25/15 · quality 45/15/25/15 · value 40/20/25/15 · equal weight 40/15/30/15.
- **C4 macro import × beta** (beta vs Nifty 50 from the NSE Index Dashboard, held in config).
- **C12 zone → percentile:** Significantly undervalued 10 · Moderately undervalued 25 · Slightly undervalued 40 · Fairly valued 50 · Slightly overvalued 60 · Moderately overvalued 75 · Significantly overvalued 90 (est.).
- **C3 factor spread** = (index PE ÷ Nifty PE) ÷ (index 5-yr median ÷ Nifty 5-yr median) − 1. Nifty PE and median are the same values as on the sector model's NIFTY50 row.
- **Look-through:** NSE factsheet sectors map to sector-model keys via `sector_map` in config; unmapped sectors (Chemicals, Diversified) use NIFTY500.
- **Two outputs + rotation:** ABSOLUTE (all buckets), RELATIVE (C3, X2, C8, C16), and a rotation rank by relative score.

## 3. Inputs, sources, frequency

| Column | Indicator | Source (first choice) | Freq |
|---|---|---|---|
| pe, pe_zone, pb_pct, pe_med5 | C1, C12, C18, C3 | indexpe.in/<slug> (headline PE, zone label, "PB is cheaper than X% of the last 5 years", 5Y median) | Monthly |
| eps5, px5 | C14, C19 | indexpe.in "5-year earnings / price growth" | Monthly |
| ret1y, ret3y, ret5y | C8, C16 | NSE **Index Dashboard** (niftyindices.com/Index_Dashboard/Index_Dashboard_MONYYYY.pdf), one PDF for all indices | Monthly |
| dy, beta (config) | info, C4 scaling | NSE Index Dashboard | Monthly |
| sector weights | X1, X2 | NSE factsheet "Sector Representation" (niftyindices.com/Factsheet/...); ALPHALV30 from dhan.co sector weightage | Monthly |
| nifty_timing, vix (NIFTY50 row) | C4, X3 | Nifty model score log `timing`; Nifty input i08 | Monthly |

indexpe.in slugs: nifty200-momentum-30, nifty-midcap150-momentum-50, nifty-alpha-50, nifty-alpha-low-volatility-30, nifty100-low-volatility-30, nifty200-quality-30, nifty-midcap150-quality-50, nifty50-value-20, nifty500-value-50, nifty50-equal-weight.

Factsheet files seen (Oct-26): Factsheet_Nifty200_Momentum30.pdf, Factsheet_NiftyMidcap150Momentum50.pdf, Factsheet_Nifty_Alpha50.pdf, Nifty100_LowVolatility30.pdf, Factsheet_Nifty200_Quality30.pdf, Factsheet_NIFTYMidcap150_Quality50.pdf, Nifty50_Value20.pdf, FactsheetNIFTY500Value50.pdf, Ind_Nifty50.pdf.

**Staleness:** flag any input older than its frequency as *(stale: date)*, estimates as *(est.)*.

## 4. How to read it

- v1 has one month of scores and no back-test. Treat 36–65 as neutral; act only at extremes (≤35 or ≥66) or on a clear relative ranking.
- **Relative/rotation is the main output.** It says which factor sleeve to tilt toward vs a Nifty 50 index fund. The absolute score says whether to deploy cash at all, and it is dominated by the same Nifty Timing input as everything else.
- Low PB percentiles (5–9) across low-vol and quality partly reflect book values that grew while prices fell. Check C18/C3 agree before acting.
- Momentum sleeves: the valuation is of the current basket, which changes at the next semi-annual rebalance (June/December).

## 5. Output template

1. **Headline:** cheapest and richest 3 factor indices (absolute → signal), top 2 and bottom 2 on the rotation rank (relative), data as-of date.
2. **Ranked table** (from `table`): index · family · absolute · signal · relative · quadrant · V/X/T/F · look-through abs/rel · indicators.
3. **Rotation table** and **family averages** (from `table`).
4. **For each index asked about:** top 3 pulls each way (value, score, Leading/Coincident/Lagging, one-line reason).
5. **Allocation read:** overweight / underweight vs Nifty 50 from the quadrant column; name a fund family from config `funds` only as an example of what tracks the index.
6. **Data quality:** indicators n/12, estimated (C12) and stale inputs, flags.
7. **Caveat line:** v1 indicative, single month, judgment anchors, not investment advice.
8. **Files:** `nifty-factors-score-log.csv`.

Plain language, tables, explain jargon the first time, phone-readable.

## 6. Change log

- 21-Nov-2026: v1 built and run for 10 factor indices. Marked indicative.

## 7. v1 vs design (what is still missing)

- No back-test and no history before Nov-26 (see design §5).
- C12 is a label-based estimate, not a measured percentile.
- MIDMOM50 uses 3-yr medians/percentiles/growth (P/E published only from Aug-2022).
- EQWT50 has no look-through (X1/X2).
- Nifty200 Value 30 left out (P/E history from Jun-2024 only).

## 8. Run log

| Run date | Month | Cheapest (abs) | Richest (abs) | Rotation: best / worst (rel) | Notes |
|---|---|---|---|---|---|
| 21-Nov-2026 | 2026-11 | ALPHALV30 37.2 · VALUE20 38.1 · QUAL30 40.3 (all Accumulate) | EQWT50 59.2 · MOM30 55.9 · VALUE50 55.3 / MIDMOM50 55.3 (Hold) | VALUE20 41.9, QUAL30 45.8 / EQWT50 69.5 (Underweight), VALUE50 63.5 | First run. Nifty timing 62.8, VIX 15.7 (19-Nov). Sector log 2026-11. No extremes on absolute |

## 9. Learnings and pitfalls

1. indexpe.in does not publish band ranges for factor indices, only a zone label. Use the label for C12 (est.) and let C18/C3 carry the precise valuation.
2. indexpe.in pages sometimes give a second PE in the performance section; use the headline.
3. Short-history indices show 3Y or 1Y medians only. Use the 3Y median as a proxy and flag it; do not use a 1Y median (that is why Value 30 is excluded).
4. The NSE Index Dashboard PDF gives returns, beta, PE/PB/DY for all indices in one fetch; prefer it to individual factsheets for returns.
5. Some factsheet extractions garble the stats block (e.g. PB read as 1.0). Cross-check against the Dashboard.
6. Year check every search result. Shell network is blocked; all data comes through web fetch.

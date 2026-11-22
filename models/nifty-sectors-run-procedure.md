# Nifty Sector / Size / Theme Indices — Standard Run Procedure (v1.0 — current release, published 20-Nov-2026)

> **Release status:** v1.0 is the live model. It uses 7 of the 17 design core indicators (3 of them as proxies) plus C18–C20, and roughly half of each sector module. The score log's `coverage` column is measured against the v1 indicator set only; `core_of_17` is the true design coverage. Always quote `core_of_17` when reporting.

Applies to any question about the 20 Nifty sectoral, size or thematic indices: "sector scores", "is Bank Nifty cheap", "which sectors to overweight", "midcap valuation", "sector rotation". Same method and same output every time. Design rationale: `nifty-sectors-model-design.md`.

Project files (all under `claude/`):
| File | Role |
|---|---|
| `nifty-sectors-model-design.md` | Full design (17 core indicators + modules). v1 implements part of it (§7 below) |
| `nifty-sectors-run-procedure.md` | This playbook |
| `sector_oscillator.py` | Canonical engine. The only scoring code to use |
| `nifty-sectors-config.json` | Per-index set-up: family, module, bucket set, primary metric, overrides, flags |
| `nifty-sectors-inputs-monthly.csv` | Long format, one row per (month, index). Raw inputs |
| `nifty-sectors-score-log.csv` | Generated scores (regenerated on every run) |

## 1. Steps

1. **Run the Nifty 50 model first** (`nifty-run-procedure.md`). Its Timing bucket score is input C4 (`nifty_timing` on the NIFTY50 row).
2. **Load** engine, config, inputs and log with `project_read`; write them to a working folder.
3. **Refresh inputs** (§3). Add rows for the new month (`month` = YYYY-MM of the run; overwrite rows for the same month). Put the date and source in `source`.
4. **Run** `python3 sector_oscillator.py all` (or `... drivers BANK IT` for chosen indices). Quote only numbers the script prints.
5. **Report** with the §5 template. Send `nifty-sectors-score-log.csv`.
6. **Save back** inputs, score log (and engine/config only if changed) with `project_write` + `local_path`. Add a §8 run-log line.

## 2. Fixed conventions

- **Score:** per indicator clamp(1 + 99 × (x − cheap)/(rich − cheap), 1, 100). High = expensive/headwind. Bands ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit.
- **Weights:** W = I × S × R × St (`SPEC` in the engine). Blanks skipped, weights re-normalised inside each bucket; a missing bucket drops out and the others are re-weighted.
- **Buckets by family** (V / S / T / F): size 40/15/30/15 · defensives 45/20/20/15 · financials 35/30/20/15 · deep cyclicals 30/35/20/15 · growth & themes 35/25/25/15.
- **Thin-bucket rule:** a bucket resting on one indicator moves only half-way from 50 (`THIN_SHRINK` 0.5).
- **C4 macro import:** halved for FMCG, Pharma, Consumption; Impact 5 for PSU Bank and Realty.
- **Two outputs:** ABSOLUTE (all buckets) and RELATIVE vs Nifty 50 (C3, C8, C16 only). Quadrant: both ≤35 → strongest buy; both ≥66 → strongest sell; relative ≤35 → overweight; relative ≥66 → underweight.
- **Vetoes:** falling knife (abs ≤35 and Filter ≥70) → "Buy vetoed"; the EPS-revision leg is not live in v1. Value-trap and concentration show as flags.
- **PE percentile** (when `pe_pct` blank) = 20 × (band − 1) + 20 × position of PE inside the band's range, from indexpe.in's 5-band split of the index's own history. PB percentile = indexpe.in's 5-yr figure.
- **Relative PE (C3)** = (index PE ÷ Nifty PE) ÷ (index 5-yr median ÷ Nifty 5-yr median) − 1. 5-yr medians avoid most of the Apr-2021 standalone → consolidated break.
- **Defence guard (C20):** Defence PE ÷ Nifty 500 PE, cheap 1.0 → rich 2.0, because its own history is short and all expensive.

## 3. Inputs, sources, frequency

| Column | Indicator | Source (first choice) | Freq |
|---|---|---|---|
| pe, pe_band, pe_band_lo/hi, pb_pct, pe_med5 | C1, C12, C3, C18 | indexpe.in/<index-slug> (headline PE; band text; "5Y median") | Monthly |
| pe_pct | C1/C12 override | Only when no band range is published (e.g. band 1 "below X") — estimate and mark "est." | Monthly |
| ret1y, ret5y | C8, C16 | indexpe.in (NSE factsheet returns, usually prior month-end) | Monthly |
| eps5, px5 | C14, C19 | indexpe.in "5-year earnings / price growth" | Monthly |
| nifty_timing (NIFTY50 row) | C4 | Nifty model `timing` from its score log | Monthly |
| S2 | MTF book YoY (size) | Same value as Nifty model i33 | Monthly |
| B1, B2 | Credit growth, credit − deposit gap | RBI fortnightly (news: "bank credit growth fortnight") | Fortnightly |
| B3 | Expected repo change ~6 m | Same as Nifty model i03 | Monthly |
| I1 | Top-IT cc revenue growth YoY | Avg of TCS, Infosys, HCLTech (+Wipro if cc given) | Quarterly |
| I2 | INR depreciation 12-m | usdinr in Nifty inputs: (now ÷ 12 m ago − 1) × 100 | Monthly |
| K1 | FMCG volume growth | NielsenIQ quarterly snapshot (volume, not value) | Quarterly |
| K2 | Food inflation | MoSPI CFPI YoY | Monthly |
| K3 | Input-cost proxy | Brent 6-m change from Nifty inputs | Monthly |
| K4 | Monsoon % of LPA | IMD season-end statement (fixed Oct → next Sep) | Yearly |
| A1 | Auto volumes YoY | FADA retail; average 2 months around Diwali shifts | Monthly |
| P1 | Domestic pharma market growth | Pharmarack MAT growth | Monthly |
| M1, M2 | Commodity vs 5-yr range; 6-m change | Brent from Nifty inputs (Energy); LME copper/alu (Metal, judgment pctl) | Monthly |
| R1, R2 | Housing sales YoY; repo level | Anarock quarterly; RBI repo | Quarterly |
| G1 | Govt capex growth | Union Budget BE vs prior BE; CGA YTD when available | Yearly/Monthly |
| G2 | Defence capital outlay growth | Union Budget | Yearly |
| S4 | Thematic-fund froth (size, CPSE, Defence, Infra) | **Automatic:** `models/amfi-thematic-monthly.csv`, refreshed daily by `scripts/fetch_amfi_thematic.py` from AMFI's monthly report (portal.amfiindia.com/spages/am<mon><yyyy>repo.xls). The engine computes the score itself (mean own-history percentile of `flow_3m_pct_aum`, `share_3m`, `new_schemes_6m`, expanding window, ≥24 months). No manual input; check only that the CSV's last month is ≤45 days old. | Monthly |

indexpe.in slugs used: nifty-50, nifty-bank, nifty-financial-services, nifty-next-50, nifty-midcap-select, nifty-midcap-150, nifty-smallcap-250, nifty-500, nifty-private-bank, nifty-psu-bank, nifty-it, nifty-auto, nifty-fmcg, nifty-pharma, nifty-metal, nifty-energy, nifty-realty, nifty-cpse, nifty-india-defence, nifty-infrastructure, nifty-india-consumption.

**Staleness:** flag any input older than its frequency as *(stale: date)*, estimates as *(est.)*.

## 4. How to read it

- v1 has **one month of scores only** (Nov-26). No back-test yet: treat 36–65 as neutral and act only at extremes (≤35 or ≥66) or on the relative score.
- The relative score is the more useful output for allocation between sectors; the absolute score says whether to deploy cash at all.
- A cyclical scoring cheap on PE near peak commodity prices is a value-trap risk (see flags).

## 5. Output template

1. **Headline:** cheapest and richest 3 indices with absolute score → signal, relative score, data as-of date.
2. **Ranked table** (from `table`): index · absolute · signal · relative · quadrant · V/S/T/F · coverage · design core n/17.
3. **For each index asked about:** top 3 pulls each way from the driver list (value, score, Leading/Coincident/Lagging, one-line reason).
4. **Allocation read:** overweight / underweight list from the quadrant column.
5. **Data quality:** design coverage (`core_of_17`, e.g. "7 of 17 core indicators"), stale and estimated inputs, flags. Do not present the `coverage` column as overall coverage.
6. **Caveat line:** single-month v1, judgment anchors, not investment advice.
7. **Files:** `nifty-sectors-score-log.csv`.

Plain language, tables, explain jargon the first time, phone-readable.

## 6. Change log

- 22-Nov-2026: **S4 thematic-fund froth added** (knowledge/board-backlog.md #17). Sector cycle bucket, weight 3×3×0.75×0.75 = 5.1, anchors 0 → 100, for the size module plus CPSE, Defence and Infra. Back-check 2019–2026: months in the top third of thematic buying were followed by a median +4–5% Nifty 500 return over 12 months vs +15–28% after the bottom third (one cycle, overlapping windows: indicative only; `scripts/research/amfi_froth_test.py`). Effect on the Nov-2026 run: −0.1 to −3.6 points on 8 indices (froth reads 24, low); Smallcap 250 Trim → Hold (65.6 → 63.3), Midcap Select Hold → Accumulate (50.4 → 49.2). Defence's Sector cycle bucket also stops being "thin" (now two indicators), which is most of its −3.6.

- 20-Nov-2026 (10:55 IST): v1.0 published as the current release at the user's request, with the partial indicator set as is. Coverage reporting rule added (quote `core_of_17`).
- 20-Nov-2026: v1 built and run for all 20 indices. Pilot on Bank, IT, FMCG, Midcap 150 first, then extended. Added C20 Defence guard and the thin-bucket rule after the first full run.

## 7. v1 vs design (what is still missing)

- Live: C1, C3, C4, C8 (1-yr proxy for 6-m), C12, C14 (5-yr proxy for TTM), C16 (5-yr proxy for 3-yr), plus new C18 (PE vs 5-yr median), C19 (5-yr re-rating), C20 (Defence guard).
- Missing core: C2 200-DMA, C5 forward PE, C6 EPS revisions, C7 BEER, C9 breadth, C10 200-WMA, C11 RSI, C13 FII/MF sector weight, C15 ROE, C17 dividend yield. These need price and consensus history the session cannot download (shell network blocked); add via a data connection or manual monthly entry.
- Euphoria veto inactive (needs C2/C9). Falling-knife veto only on the Filter leg.
- No history before Nov-26: build monthly back-fill from NSE PE/PB/DY history, then back-test 12/36-m relative returns.

## 8. Run log

| Run date | Month | Cheapest (abs) | Richest (abs) | Notes |
|---|---|---|---|---|
| 20-Nov-2026 | 2026-11 | IT 27.9 Buy · FMCG 38.2 · Next 50 39.0 | Pharma 72.7 Trim · Smallcap 250 65.6 Trim · Metal 64.1 | First run. Design core coverage 6–7 of 17. Nifty timing 62.8 (19-Nov) |

## 9. Learnings and pitfalls

1. indexpe.in pages sometimes show two PE values (headline vs band text). Use the headline; the band range still sets the percentile.
2. Band 1 and band 5 publish only one edge ("below X" / "above X"): estimate `pe_pct` (or set a nominal far edge) and mark est.
3. Year check every search result (see Nifty §9 pitfall 1).
4. FADA October/November YoY swings with the Diwali date; average two months.
5. Shell network is blocked; all data comes through web fetch. niftyindices.com history needs a different route.

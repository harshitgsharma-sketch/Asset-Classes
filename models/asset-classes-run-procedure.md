# Asset-Class Valuation Model — Standard Run Procedure (v1, 21-Nov-2026)

> **Release status:** v1. 15 asset classes, 37 indicators, one month of scores, judgment anchors, no back-test. Report as **indicative** and act only at the extremes (≤35 or ≥66).

Applies to: "rate all asset classes", "which asset is cheapest", "where should I put new money", "equity vs debt vs gold vs property", "asset allocation tilt", or a valuation question on silver, G-secs, corporate bonds, credit, short-term debt, cash, REITs, residential property or US Treasuries. Design: `asset-classes-model-design.md`.

| File (`claude/`) | Role |
|---|---|
| `asset-classes-model-design.md` | Principles, universe, indicators and anchors, weaknesses |
| `asset-classes-run-procedure.md` | This playbook |
| `asset_class_oscillator.py` | Canonical engine. The only scoring code to use |
| `asset-classes-config.json` | Assets, indicators, anchors, weights (editable) |
| `asset-classes-inputs-monthly.csv` | One row per month of raw inputs (wide format) |
| `asset-classes-score-log.csv` | Output, regenerated every run |

## 1. Steps

1. **Run order:** gold → Nifty 50 → sectors → global → **asset classes**. This model imports their Valuation buckets and oscillators, so use their latest logs. If they were not re-run this month, reuse their last values and flag them *(stale: date)*.
2. **Load** the engine, config, inputs and log with `project_read`; write them to a working folder.
3. **Refresh inputs** (§3). Add or overwrite the row for the run month (`month` = YYYY-MM). Record every value's date and source in `source`; mark judgment values "est.".
4. **Run** `python3 asset_class_oscillator.py all` (or `drivers KEY ...`, `table`, `chart`). Quote only numbers the script prints.
5. **Report** with the §5 template. Send `asset-classes-valuation.png` and `asset-classes-score-log.csv`.
6. **Save back** inputs and score log (engine and config only if changed) with `project_write` + `local_path`; add a §7 run-log line.

## 2. Fixed conventions

- Score 1 = cheap vs own history, 100 = rich. Labels and tilts as in the design §2.
- **Shared inputs** must equal the other models' same-month values: Nifty close and EPS, gold, silver, USD/INR, INR REER (Nifty i31), repo, CPI, UST 10-yr, S&P fwd PE, ACWI fwd PE.
- **Imported columns:** `imp_nifty_v` (Nifty score log `valuation`), `imp_mid_v` / `imp_small_v` (sector log `valuation` for MIDCAP150 / SMALLCAP250), `imp_acwi_v` / `imp_sp500_v` (global log `valuation` for ACWI / SP500), `imp_gold_v` (gold log `valuation`). `osc_*` = each model's headline oscillator (global: INR score).
- **Expected CPI (`cpi_exp1y`)** = 12-month-ahead CPI from the latest RBI MPC projection path; **`repo_exp1y`** = expected average repo over the next 12 months (OIS / consensus). Both est. until a market source is used.
- **36-m averages** for gold and silver = mean of (USD price × USD/INR) over the last 36 month-ends from `gold-inputs-monthly.csv`.

## 3. Inputs and sources

| Column | First source | Freq |
|---|---|---|
| gsec10, gsec5, gsec3, aaa1y, aaa5y, aa3y | Aditya Birla Sun Life MF "Daily Fixed Income Tracker" PDF (yield + spread monitor); Trading Economics India 10Y news | Weekly |
| repo, cpi_exp1y | RBI MPC resolution (projection table) | After MPC |
| cpi_yoy | MoSPI CPI release (~12th) | Monthly |
| tbill91 | RBI weekly T-bill auction press release | Weekly |
| fd1y | SBI retail FD card (sbi.bank.in) | Monthly |
| mid150_pe, small250_pe | indexpe.in / NSE Indices (as in the sector model) | Monthly |
| sp500_fpe, us10y, acwi_fpe | Global model inputs (FactSet, MSCI) | Monthly |
| tips10 | FRED DFII10 | Weekly |
| inr_reer | Nifty inputs i31 (RBI Bulletin table, 40-currency) | Monthly |
| reit_yield | Median distribution yield of listed REITs (Indian REITs Association, broker notes; or annualised latest DPU ÷ price for Embassy, Mindspace, Brookfield, Nexus, KRT) | Quarterly |
| rent_yield, house_px_cagr | Anarock / Knight Frank city reports (top-7 average) | Half-yearly |
| home_loan | Typical SBI/HDFC new-borrower rate (Business Standard monthly home-loan table) | Monthly |
| income_cagr | Nominal GDP (or per-capita income) CAGR over the same window (MoSPI) | Yearly |

## 4. How to read it

- Compare across assets only through the score; the raw yields differ by design.
- A low score on a debt asset means its **yield is high vs its own history** (lock in duration or carry), not that its price will jump.
- Foreign assets: a low INR REER pushes their score up — the rupee is cheap, so buying dollars is dear. That is a currency call on top of the asset's own valuation.
- When the valuation score and the asset's own-model oscillator disagree, the oscillator (which adds timing and filter) decides *when*; this score says *what* is cheap.

## 5. Output template

1. **Headline:** cheapest and richest asset classes (score → label), data as-of date.
2. **Ranked table** (from `table`): asset · score · label · tilt · income yield · own-model oscillator (where one exists).
3. **By family:** average score for Indian bonds, Foreign bonds, Cash, Precious metals, Indian equity, Foreign equity, Real estate.
4. **For each asset asked about (or the 2 cheapest and 2 richest):** the drivers from `drivers` (value, score, Leading/Coincident/Lagging, one-line reason).
5. **Allocation read:** which assets to tilt towards / away from a strategic mix (never a full allocation).
6. **Data quality:** estimated inputs, stale imports, thin assets, §4 weaknesses of the design.
7. **Caveat line:** v1, one month, judgment anchors, not investment advice.
8. **Files:** chart PNG and score log.

Plain language, tables, explain jargon the first time, phone-readable.

## 6. Change log

- 21-Nov-2026: v1 built at the user's request ("rate all asset classes on valuation for someone living in India"). 15 assets, 37 indicators. Short-debt B7 measured against the expected repo path (not spot repo) so priced-in hikes don't make it look artificially cheap.

## 7. Run log

| Run date | Month | Cheapest | Richest | Notes |
|---|---|---|---|---|
| 21-Nov-2026 | 2026-11 | Short-term debt 9.6 · US Treasuries 24.1 · Long G-secs 33.6 (Cheap) | REITs 88.0 · US equity 71.1 · Smallcaps 67.8 (Expensive) | First run. Nifty 54.6, Midcap 52.0, Gold 57.9, Silver 38.2, ACWI 64.6, AAA 44.3, AA 42.7, Cash 47.8, Residential 44.9. Families: foreign bonds 24.1 · Indian bonds 32.6 · cash 47.8 · metals 48.0 · Indian equity 58.1 · real estate 66.4 · foreign equity 67.8 |

## 8. Learnings and pitfalls

1. Put the **year in every search**; the ABSL fixed-income tracker has identically named 2025 files (e.g. "…-19-nov-2025.pdf").
2. The 10-yr G-sec moved 7.12 → 7.34 within November 2026; the Nifty CSV still had 7.20 (19-Nov). Refresh it in the Nifty inputs on the next Nifty run so both models agree.
3. The AA 3-yr spread computed from the tracker's yield table (183 bp) differs from its own spread monitor (~160 bp) because the monitor uses a different date/benchmark. Use the yield table consistently.
4. REIT yields: the "6.8–7.5% average yield" figures in the press are multi-year averages; use the **current** median (5.8% on 24-Sep-2026) or annualised latest DPU ÷ price.
5. Knight Frank affordability articles quote different MMR numbers (47% for 2025, 69% for H1-2026) — check the report before using affordability as an indicator.
